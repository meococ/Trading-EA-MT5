#!/usr/bin/env python3
"""Claim-first, comparator-only recovery of the immutable HYP009 Model-0 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV2"
RESEARCH = PACKAGE / "research"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
GITIGNORE = ROOT / ".gitignore"
HYPOTHESIS = "HYP-STBS-XAUUSD-M15-010"
PARENT = "HYP-STBS-XAUUSD-M15-009"
ATTEMPT = "STBS010-COMPARATOR-001"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
AUTHORITY_VERDICT = "FROZEN_STBS010_EXISTING_RUN_COMPARATOR_AUTHORIZED"
PASS_VERDICT = "ENGINEERING_VALID_STBS009_MODEL0_SIGNAL_ATR_GEOMETRY_PARITY_RECOVERED_NO_TRADES"
OUTPUT_ROOT = RESEARCH / "evidence" / HYPOTHESIS / ATTEMPT
PREREG = RESEARCH / "HYP-STBS-XAUUSD-M15-010_EXISTING_RUN_COMPARATOR_PREREG.md"
TEST = PACKAGE / "tests" / "test_stbs010_existing_run_comparator.py"
REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-010_PRE_COMPARATOR_REVIEW.md"
BASE = RESEARCH / "run_stbs009_model0_audit.py"
BASE_SHA256 = "AFFD1823BBEA9833C6C7D4844A829135277E808A2114142BBA28BE4AA0100E42"
PARENT_TERMINAL_ROW_SHA256 = "100610B9EC9D4383E9EEA892AC7254EF43DAD2015BE51AA0764465B4837508A3"
PARENT_TERMINAL_VERDICT = "KILL_EXACT_RUNNER_COMPILE_LOG_SUFFIX_FALSE_REJECT_AFTER_MT5_NO_PARITY_NO_ECONOMICS"
ORACLE_SHA256 = "63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096"
SOURCE_SHA256 = "D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB"
RUN_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SupertrendBurstScalperTradeV2" / "20260809_181119"
PARENT_ATTEMPT_ROOT = RESEARCH / "evidence" / PARENT / "STBS009-MODEL0-AUDIT-001"
PARENT_FAILURE = RESEARCH / "HYP-STBS-XAUUSD-M15-009_COMPILE_LOG_SUFFIX_FAILURE.md"
PARENT_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-009_INDEPENDENT_FAILURE_REVIEW.md"
PARENT_RUN_COMPILE_LOG = PARENT_ATTEMPT_ROOT / "run_compile_log.bin"
PARENT_PACKET_RECEIPT = RESEARCH / "preflight" / PARENT / "V1" / "contract_receipt.control.json"
ORACLE = ROOT / (
    "03. EA Developer/EA_SupertrendStateFlip/research/evidence/"
    "HYP-ST-XAUUSD-H1-003/ST003-ORACLE-001/st003_source_parity_oracle.jsonl"
)
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV2.mq5"
EXPECTED_COUNTS = {
    "raw": 690, "executable": 683, "gaps": 7, "long": 339,
    "short": 344, "atr_ready": 683, "geometry_ready": 683,
}
EXPECTED_DATA_ACCEPTANCE = {
    "history_quality_operator": "gt", "history_quality_threshold_pct": 97,
    "coverage_mode": "fixed_window", "mandatory_symbols": ["XAUUSD"],
    "no_skip": True, "require_tester_journal_bounds": True,
    "require_series_proof": True,
}
TRUE_AUTHORITIES = ("artifact_collection_authorized", "comparator_execution_authorized")
FALSE_AUTHORITIES = (
    "packet_build_authorized", "model0_audit_run_authorized", "mt5_authorized",
    "model0_authorized", "model0_data_acquisition_authorized",
    "model0_performance_authorized", "model4_authorized",
    "model4_data_acquisition_authorized", "model4_performance_authorized",
    "source_run_authorized", "compile_authorized", "run_compile_authorized",
    "mql5_compile_authorized", "standalone_compile_authorized",
    "trade_api_authorized", "performance_metrics_authorized",
    "outcome_prices_authorized", "post_event_ohlc_authorized",
    "visual_mode_authorized", "network_authorized", "paid_requests_authorized",
    "economics_authorized", "optimization_authorized", "validation_authorized",
    "holdout_authorized", "research_validation_access_authorized",
    "research_holdout_access_authorized", "validation_access_authorized",
    "holdout_access_authorized", "research_falsification_authorized",
    "economic_validity_authorized", "promotion_eligible", "paper_trading_authorized",
    "live_trading_authorized", "market_edge_claim_authorized",
    "same_id_retry_authorized", "registry_mutation_allowed",
)

PARENT_BINDINGS: dict[str, tuple[Path, str]] = {
    "parent_runner": (BASE, BASE_SHA256),
    "parent_packet_receipt": (
        PARENT_PACKET_RECEIPT,
        "23A8320468CAB893B12088546F811A2241939751BEDED896E046F56723F9B818",
    ),
    "parent_oracle": (ORACLE, ORACLE_SHA256),
    "canonical_source": (SOURCE, SOURCE_SHA256),
    "parent_attempt_started": (
        PARENT_ATTEMPT_ROOT / "attempt_started.json",
        "07B3F4EA4A33577B58A3AFC528F4FD56D4D9DC35512F244FCFA7EF403EAB0F4E",
    ),
    "parent_attempt_terminal": (
        PARENT_ATTEMPT_ROOT / "attempt_terminal.json",
        "9EDFC70DDAD82B0B446678AB6A135573DC2D9CA1919BE7F8F0ED14FFDE11A565",
    ),
    "parent_alpha_stdout": (
        PARENT_ATTEMPT_ROOT / "alpha_stdout.log",
        "F75363F2EC88587E79958371308C778A96AC55B7645F79AB039CECC83F96F29F",
    ),
    "parent_alpha_stderr": (
        PARENT_ATTEMPT_ROOT / "alpha_stderr.log",
        "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
    ),
    "parent_run_compile_log": (
        PARENT_RUN_COMPILE_LOG,
        "7DCEC7E9B9D8CFDD19CE507CF1D49258F91AA17B200475404A58E9922C9A070E",
    ),
    "parent_failure": (
        PARENT_FAILURE,
        "C77B1D131644D865D6FA70DF0AB7E5D950972B210380959E6F627C359E7BAE63",
    ),
    "parent_failure_review": (
        PARENT_REVIEW,
        "36E76968AE81662ABD6C7A120EBD6D231488576A6B1197548DC190795CF17EF1",
    ),
    "run_manifest": (
        RUN_DIR / "run_manifest.json",
        "8837FB5635865AA5791181D22E7F16418C63A5D39A5F235D59539E38B2F3C5E5",
    ),
    "run_report": (
        RUN_DIR / "report.html",
        "9B4872DEEBB9B4D41284EF010ED68E5DC5FB13F5A19490DE0A50573737C46E8E",
    ),
    "run_journal": (
        RUN_DIR / "logs" / "tester_journal_delta.log",
        "D7851DB3E53515E063C79854841D62D5A7E91D1BD8A75B2DD64849689F3CBDA0",
    ),
    "run_summary": (
        RUN_DIR / "analysis" / "enhanced_summary.json",
        "E546E60F4587CE4572AE7526BAABC737F8A65FAF7542A96359A092E893C8DA47",
    ),
    "run_source_snapshot": (
        RUN_DIR / "snapshot" / "source" / "EA_SupertrendBurstScalperTradeV2.mq5",
        SOURCE_SHA256,
    ),
    "run_ex5_snapshot": (
        RUN_DIR / "snapshot" / "build" / "EA_SupertrendBurstScalperTradeV2.ex5",
        "3E71B8B74E18F407FFA645118D6ED10FFBC040B7F5044E53C3F28A3C5E7883C9",
    ),
    "run_config_snapshot": (
        RUN_DIR / "snapshot" / "config" / "config.ini",
        "CCCDB49CA74BB216EAB05F11A105629E1ADE1BFAC101C54CFF1D64E22BCC3A27",
    ),
}


def now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def write_exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def latest_row(registry_raw: bytes, hypothesis: str) -> tuple[bytes, dict[str, Any]]:
    found: tuple[bytes, dict[str, Any]] | None = None
    for raw in registry_raw.splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == hypothesis:
            found = raw, row
    if found is None:
        raise ValueError(f"registry has no {hypothesis}")
    return found


def claim(registry: Path) -> Path:
    if registry.resolve() != REGISTRY.resolve():
        raise ValueError("registry path is not canonical")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    marker = OUTPUT_ROOT / "attempt_started.json"
    write_exclusive(marker, json_bytes({
        "schema_version": "stbs010_comparator_started.v1",
        "hypothesis_id": HYPOTHESIS,
        "attempt_id": ATTEMPT,
        "started_at_utc": now_text(),
        "declared_registry_path": str(REGISTRY.resolve()),
        "same_id_retry_authorized": False,
    }))
    return marker


def require_file(path: Path, expected: str, label: str) -> dict[str, str]:
    if not re.fullmatch(r"[A-F0-9]{64}", expected or "") or not path.is_file():
        raise ValueError(f"{label} is absent or has an invalid frozen hash")
    actual = sha_file(path)
    if actual != expected:
        raise ValueError(f"{label} changed: expected {expected}, got {actual}")
    return {"label": label, "path": str(path.resolve()), "sha256": actual}


def load_parent_runner() -> types.ModuleType:
    raw = BASE.read_bytes()
    if sha_bytes(raw) != BASE_SHA256:
        raise ValueError("frozen HYP009 runner changed")
    name = "stbs010_frozen_hyp009_runner"
    module = types.ModuleType(name)
    module.__file__ = str(BASE)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(raw, str(BASE), "exec"), module.__dict__)
    if (
        module.ORACLE_SHA256 != ORACLE_SHA256
        or Path(module.ORACLE).resolve() != ORACLE.resolve()
        or sha_file(module.ORACLE) != ORACLE_SHA256
        or Path(module.RUN_COMPILE_LOG_ARCHIVE).resolve() != PARENT_RUN_COMPILE_LOG.resolve()
    ):
        raise ValueError("frozen ST003 oracle dependency changed")
    return module


def validate_authority_after_claim(registry: Path) -> tuple[dict[str, Any], dict[str, str], list[dict[str, str]]]:
    registry_raw = registry.read_bytes()
    raw, row = latest_row(registry_raw, HYPOTHESIS)
    parent_raw, parent = latest_row(registry_raw, PARENT)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    issued = datetime.fromisoformat(str(row.get("updated_at_utc", "")).replace("Z", "+00:00"))
    self_path = Path(__file__).resolve()
    checks = {
        "state": row.get("state") == "screened",
        "parent": row.get("parent_candidate") == PARENT,
        "verdict": row.get("verdict") == AUTHORITY_VERDICT,
        "ea": row.get("ea_name") == "EA_SupertrendBurstScalperTradeV2",
        "symbol_timeframe": row.get("symbol") == "XAUUSD" and row.get("timeframe") == "M15",
        "window": row.get("window") == {"from": "2018.01.01", "to": "2022.12.31"},
        "model": row.get("model") == 0,
        "source": row.get("source_hash") == SOURCE_SHA256,
        "overrides": row.get("exact_overrides") == "InpAuditOnly=true",
        "evidence_kind": row.get("evidence_contract_kind") == "data_acquisition",
        "data_acceptance": row.get("data_acceptance_contract") == EXPECTED_DATA_ACCEPTANCE,
        "no_economic_acceptance": row.get("acceptance_contract") is None,
        "authority": validation.get("authority") == AUTHORITY,
        "attempt_id": validation.get("comparator_attempt_id") == ATTEMPT,
        "attempt_limit": validation.get("comparator_attempt_limit") == 1
        and metrics.get("comparator_attempt_limit") == 1,
        "unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "zero_runs": metrics.get("model0_runs") == 0 and metrics.get("mt5_launches") == 0,
        "zero_exposure": metrics.get("orders_executed") == 0
        and metrics.get("trades_simulated") == 0 and metrics.get("returns_computed") == 0,
        "zero_trials": metrics.get("performance_trials_executed") == 0
        and metrics.get("economics_executed") is False,
        "validation_unopened": metrics.get("research_validation_opened") is False,
        "holdout_unopened": metrics.get("research_holdout_opened") is False,
        "no_run_ids": row.get("run_ids") == [],
        "true_authorities": all(validation.get(name) is True for name in TRUE_AUTHORITIES),
        "false_authorities": all(validation.get(name) is False for name in FALSE_AUTHORITIES),
        "self_path": validation.get("reviewed_comparator_path")
        == self_path.relative_to(ROOT).as_posix(),
        "self_sha": validation.get("reviewed_comparator_sha256") == sha_file(self_path),
        "base_path": validation.get("reviewed_hyp009_runner_path") == BASE.relative_to(ROOT).as_posix(),
        "base_sha": validation.get("reviewed_hyp009_runner_sha256") == BASE_SHA256,
        "prereg_path": row.get("prereg_path") == PREREG.relative_to(ROOT).as_posix(),
        "prereg_sha": row.get("prereg_sha256") == sha_file(PREREG),
        "test_path": validation.get("reviewed_test_path") == TEST.relative_to(ROOT).as_posix(),
        "test_sha": validation.get("reviewed_test_sha256") == sha_file(TEST),
        "review_path": validation.get("independent_review_path") == REVIEW.relative_to(ROOT).as_posix(),
        "review_sha": validation.get("independent_review_sha256") == sha_file(REVIEW),
        "review_status": validation.get("independent_review_status") == "PASS_PRE_COMPARATOR",
        "gitignore_path": validation.get("gitignore_path") == GITIGNORE.relative_to(ROOT).as_posix(),
        "gitignore_sha": validation.get("gitignore_sha256") == sha_file(GITIGNORE),
        "evidence_root": validation.get("comparator_evidence_root")
        == OUTPUT_ROOT.relative_to(ROOT).as_posix(),
        "parent_state": parent.get("state") == "killed",
        "parent_verdict": parent.get("verdict") == PARENT_TERMINAL_VERDICT,
        "parent_raw": sha_bytes(parent_raw) == PARENT_TERMINAL_ROW_SHA256
        and validation.get("hyp009_terminal_row_sha256") == PARENT_TERMINAL_ROW_SHA256,
        "nonfuture": issued <= datetime.now(timezone.utc),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP010 comparator authority failed: {failed}")
    review_text = REVIEW.read_text(encoding="utf-8", errors="strict")
    if not review_text.startswith("# HYP010 pre-comparator independent review\n\nVerdict: `PASS_PRE_COMPARATOR`\n"):
        raise ValueError("independent review semantics are not PASS_PRE_COMPARATOR")
    bindings = [
        require_file(self_path, validation["reviewed_comparator_sha256"], "comparator"),
        require_file(PREREG, row["prereg_sha256"], "prereg"),
        require_file(TEST, validation["reviewed_test_sha256"], "reviewed_test"),
        require_file(REVIEW, validation["independent_review_sha256"], "independent_review"),
        require_file(GITIGNORE, validation["gitignore_sha256"], "gitignore"),
    ]
    for label, (path, expected) in PARENT_BINDINGS.items():
        bindings.append(require_file(path, expected, label))
    return row, {
        "registry_sha256": sha_bytes(registry_raw),
        "latest_row_sha256": sha_bytes(raw),
        "hyp009_terminal_row_sha256": sha_bytes(parent_raw),
    }, bindings


RESULT_LINE = re.compile(
    r"Result: ([0-9]+) errors, ([0-9]+) warnings, ([0-9]+) ms elapsed, cpu='([^']+)'"
)


def decode_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="strict")
    return raw.decode("utf-8-sig", errors="strict")


def parse_structured_compile_result(path: Path) -> dict[str, Any]:
    result_lines = [line.strip() for line in decode_text(path).splitlines()
                    if line.strip().startswith("Result:")]
    if len(result_lines) != 1:
        raise ValueError(f"compile log must contain exactly one Result line, got {len(result_lines)}")
    match = RESULT_LINE.fullmatch(result_lines[0])
    if match is None:
        raise ValueError("compile Result line does not match the frozen structured suffix contract")
    errors, warnings, elapsed_ms = (int(match.group(index)) for index in (1, 2, 3))
    cpu = match.group(4)
    if errors != 0 or warnings != 0 or elapsed_ms <= 0 or cpu != "X64 Regular":
        raise ValueError("compile Result values fail 0E/0W/positive-elapsed/exact-CPU gates")
    return {
        "errors": errors, "warnings": warnings, "elapsed_ms": elapsed_ms,
        "cpu": cpu, "line": result_lines[0],
    }


def recovered_validate_run(base: types.ModuleType) -> tuple[dict[str, Any], dict[str, Any]]:
    compile_result = parse_structured_compile_result(PARENT_RUN_COMPILE_LOG)
    original_decode = base.decode_artifact

    def compatibility_decode(path: Path) -> str:
        text = original_decode(path)
        if Path(path).resolve() == PARENT_RUN_COMPILE_LOG.resolve():
            exact = compile_result["line"]
            if text.count(exact) != 1:
                raise ValueError("structured compile line changed during recovered validation")
            return text.replace(exact, "Result: 0 errors, 0 warnings", 1)
        return text

    base.decode_artifact = compatibility_decode
    try:
        validated = base.validate_run(RUN_DIR.resolve())
    finally:
        base.decode_artifact = original_decode
    if validated.get("counts") != {**EXPECTED_COUNTS, "journal_record_multiplicity": 2}:
        raise ValueError("recovered journal count/multiplicity contract changed")
    return validated, compile_result


def build_report(base: types.ModuleType) -> tuple[dict[str, Any], list[dict[str, str]]]:
    before = {label: sha_file(path) for label, (path, _) in PARENT_BINDINGS.items()}
    validated, compile_result = recovered_validate_run(base)
    after = {label: sha_file(path) for label, (path, _) in PARENT_BINDINGS.items()}
    if before != after:
        raise ValueError("bound parent/run artifact changed during comparison")
    extra_bindings: list[dict[str, str]] = []
    seen = {path.resolve() for path, _ in PARENT_BINDINGS.values()}
    for label in (
        "source_snapshot", "ex5_snapshot", "config_snapshot", "staged_ex5",
        "live_config", "manifest", "report", "journal", "summary", "run_compile_log",
    ):
        path = Path(validated[label]).resolve()
        if path not in seen:
            extra_bindings.append({"label": label, "path": str(path), "sha256": sha_file(path)})
            seen.add(path)
    report = {
        "schema_version": "stbs010_existing_run_comparator_report.v1",
        "hypothesis_id": HYPOTHESIS,
        "target_hypothesis_id": PARENT,
        "target_run_id": RUN_DIR.name,
        "verdict": PASS_VERDICT,
        "compile_result": compile_result,
        "history_quality": validated["history_quality"],
        "actual_from": validated["actual_from"],
        "actual_to": validated["actual_to"],
        **validated["counts"],
        "manifest_contract": "PASS",
        "config_contract": "PASS",
        "data_quality_and_series_proof": "PASS",
        "empty_orders_and_exact_funding": "PASS",
        "st003_signal_clock_direction_geometry_parity": "PASS",
        "strategy_requests": 0,
        "orders_executed": 0,
        "trades_executed": 0,
        "outcomes_read": 0,
        "performance_metrics_authorized": False,
        "economics_evaluated": False,
    }
    return report, extra_bindings


def execute(registry: Path) -> dict[str, Any]:
    marker = claim(registry)
    terminal = OUTPUT_ROOT / "attempt_terminal.json"
    try:
        _, authority, bindings = validate_authority_after_claim(registry.resolve())
        base = load_parent_runner()
        first, first_extra = build_report(base)
        second, second_extra = build_report(base)
        report_raw = json_bytes(first)
        if report_raw != json_bytes(second) or first_extra != second_extra:
            raise ValueError("full recovered comparator replay is not byte deterministic")
        for item in bindings + first_extra:
            if sha_file(Path(item["path"])) != item["sha256"]:
                raise ValueError(f"bound input changed before receipt sealing: {item['label']}")
        report_path = OUTPUT_ROOT / "stbs010_existing_run_comparator_report.json"
        write_exclusive(report_path, report_raw)
        receipt = {
            "schema_version": "stbs010_existing_run_comparator_receipt.v1",
            "hypothesis_id": HYPOTHESIS,
            "attempt_id": ATTEMPT,
            "verdict": PASS_VERDICT,
            "authority": authority,
            "attempt_started_sha256": sha_file(marker),
            "report_sha256": sha_bytes(report_raw),
            "bindings": bindings + first_extra,
            "deterministic_replay": "PASS",
            "mt5_launches": 0,
            "compile_attempts": 0,
            "orders_executed": 0,
            "trades_executed": 0,
            "outcomes_read": 0,
            "performance_metrics_authorized": False,
            "economics_evaluated": False,
            "same_id_retry_authorized": False,
            "completed_at_utc": now_text(),
        }
        receipt_raw = json_bytes(receipt)
        receipt_path = OUTPUT_ROOT / "stbs010_existing_run_comparator_receipt.json"
        write_exclusive(receipt_path, receipt_raw)
        write_exclusive(terminal, json_bytes({
            "schema_version": "stbs010_existing_run_comparator_terminal.v1",
            "hypothesis_id": HYPOTHESIS,
            "attempt_id": ATTEMPT,
            "status": "COMPLETE",
            "verdict": PASS_VERDICT,
            "completed_at_utc": now_text(),
            "attempt_started_sha256": sha_file(marker),
            "report_sha256": sha_bytes(report_raw),
            "receipt_sha256": sha_bytes(receipt_raw),
            "same_id_retry_authorized": False,
        }))
        return first
    except BaseException as exc:
        if not terminal.exists():
            write_exclusive(terminal, json_bytes({
                "schema_version": "stbs010_existing_run_comparator_terminal.v1",
                "hypothesis_id": HYPOTHESIS,
                "attempt_id": ATTEMPT,
                "status": "FAILED",
                "verdict": "STBS010_COMPARATOR_FAILED_CONSUMED",
                "completed_at_utc": now_text(),
                "failure_type": type(exc).__name__,
                "failure": str(exc),
                "attempt_started_sha256": sha_file(marker),
                "same_id_retry_authorized": False,
            }))
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()
    print(json.dumps(execute(args.registry), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
