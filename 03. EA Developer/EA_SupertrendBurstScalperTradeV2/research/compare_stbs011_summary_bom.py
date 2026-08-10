#!/usr/bin/env python3
"""Claim-first final engineering recovery for the exact HYP009 summary BOM."""

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
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV2"
RESEARCH = PACKAGE / "research"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
GITIGNORE = ROOT / ".gitignore"
HYPOTHESIS = "HYP-STBS-XAUUSD-M15-011"
PARENT = "HYP-STBS-XAUUSD-M15-010"
ATTEMPT = "STBS011-COMPARATOR-001"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
AUTHORITY_VERDICT = "FROZEN_STBS011_SUMMARY_BOM_COMPARATOR_AUTHORIZED"
PASS_VERDICT = "ENGINEERING_VALID_STBS009_MODEL0_SIGNAL_ATR_GEOMETRY_PARITY_RECOVERED_NO_TRADES"
OUTPUT_ROOT = RESEARCH / "evidence" / HYPOTHESIS / ATTEMPT
PREREG = RESEARCH / "HYP-STBS-XAUUSD-M15-011_SUMMARY_BOM_COMPARATOR_PREREG.md"
TEST = PACKAGE / "tests" / "test_stbs011_summary_bom_comparator.py"
REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-011_PRE_COMPARATOR_REVIEW.md"
HYP010_COMPARATOR = RESEARCH / "compare_stbs010_existing_run.py"
HYP010_COMPARATOR_SHA256 = "6B5357466E5EC6D17375C6F6D8D5BE2B421CC2B70E1EB223226CD15A7EAD564A"
PARENT_TERMINAL_ROW_SHA256 = "D951D4D552BD8BFE4CE197047647FCDD99DA825FA605001B81727634EF26AD74"
PARENT_TERMINAL_VERDICT = "KILL_EXACT_ZERO_TRADE_SUMMARY_UTF8_BOM_DECODER_NO_PARITY_NO_ECONOMICS"
PARENT_ATTEMPT_ROOT = RESEARCH / "evidence" / PARENT / "STBS010-COMPARATOR-001"
PARENT_FAILURE = RESEARCH / "HYP-STBS-XAUUSD-M15-010_SUMMARY_BOM_FAILURE.md"
PARENT_FAILURE_SHA256 = "A74AD9D4708E247C7EEAB5AFB2D24711C9242C8E0734BD815B4EBCE6FC978271"
PARENT_FAILURE_REVIEW = RESEARCH / "HYP-STBS-XAUUSD-M15-010_INDEPENDENT_FAILURE_REVIEW.md"
PARENT_FAILURE_REVIEW_SHA256 = "DF999B8FEDE95F05349073308C2F0BDA8EAE99B4815F1FF5D0AB3247FFB4ADC0"
RUN_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SupertrendBurstScalperTradeV2" / "20260809_181119"
SUMMARY = RUN_DIR / "analysis" / "enhanced_summary.json"
SUMMARY_SHA256 = "E546E60F4587CE4572AE7526BAABC737F8A65FAF7542A96359A092E893C8DA47"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV2.mq5"
SOURCE_SHA256 = "D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB"
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
    "hyp010_comparator": (HYP010_COMPARATOR, HYP010_COMPARATOR_SHA256),
    "hyp010_attempt_started": (
        PARENT_ATTEMPT_ROOT / "attempt_started.json",
        "595E055332AAEFFC738812F213CBDF6593FD44295548E292EEE79DAF1EAE66D6",
    ),
    "hyp010_attempt_terminal": (
        PARENT_ATTEMPT_ROOT / "attempt_terminal.json",
        "E0CD5B3DE7A2332CBD8C4BB729B23141D29DC940F3C13A8A173D0DB8A8686AE5",
    ),
    "hyp010_failure": (PARENT_FAILURE, PARENT_FAILURE_SHA256),
    "hyp010_failure_review": (PARENT_FAILURE_REVIEW, PARENT_FAILURE_REVIEW_SHA256),
    "frozen_summary": (SUMMARY, SUMMARY_SHA256),
    "canonical_source": (SOURCE, SOURCE_SHA256),
}
UTF8_BOM = b"\xef\xbb\xbf"


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
        if raw.strip():
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
        "schema_version": "stbs011_comparator_started.v1",
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


def load_hyp010() -> types.ModuleType:
    raw = HYP010_COMPARATOR.read_bytes()
    if sha_bytes(raw) != HYP010_COMPARATOR_SHA256:
        raise ValueError("frozen HYP010 comparator changed")
    name = "stbs011_frozen_hyp010_comparator"
    module = types.ModuleType(name)
    module.__file__ = str(HYP010_COMPARATOR)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(raw, str(HYP010_COMPARATOR), "exec"), module.__dict__)
    summary_path, summary_hash = module.PARENT_BINDINGS["run_summary"]
    if Path(summary_path).resolve() != SUMMARY.resolve() or summary_hash != SUMMARY_SHA256:
        raise ValueError("unexpected HYP010 summary dependency")
    return module


def decode_exact_bom_json(
    path: Path,
    *,
    expected_path: Path = SUMMARY,
    expected_sha256: str = SUMMARY_SHA256,
) -> tuple[str, Any]:
    if path.resolve() != expected_path.resolve():
        raise ValueError("summary BOM decoder used on a non-authorized path")
    raw = path.read_bytes()
    if sha_bytes(raw) != expected_sha256:
        raise ValueError("summary BOM decoder input hash changed")
    if not raw.startswith(UTF8_BOM) or raw.startswith(UTF8_BOM + UTF8_BOM):
        raise ValueError("summary must begin with exactly one UTF-8 BOM")
    payload_raw = raw[len(UTF8_BOM):]
    if UTF8_BOM in payload_raw:
        raise ValueError("summary contains an additional/interior UTF-8 BOM")
    text = payload_raw.decode("utf-8", errors="strict")
    payload = json.loads(text)
    return text, payload


def validate_authority_after_claim(registry: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    registry_raw = registry.read_bytes()
    raw, row = latest_row(registry_raw, HYPOTHESIS)
    parent_raw, parent = latest_row(registry_raw, PARENT)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    self_path = Path(__file__).resolve()
    issued = datetime.fromisoformat(str(row.get("updated_at_utc", "")).replace("Z", "+00:00"))
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
        "no_economic_contract": row.get("acceptance_contract") is None,
        "authority": validation.get("authority") == AUTHORITY,
        "attempt": validation.get("comparator_attempt_id") == ATTEMPT,
        "limit": validation.get("comparator_attempt_limit") == 1
        and metrics.get("comparator_attempt_limit") == 1,
        "unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "no_runs": metrics.get("model0_runs") == 0 and metrics.get("mt5_launches") == 0,
        "no_orders": metrics.get("orders_executed") == 0 and metrics.get("trades_simulated") == 0,
        "no_returns": metrics.get("returns_computed") == 0
        and metrics.get("performance_trials_executed") == 0,
        "no_economics": metrics.get("economics_executed") is False,
        "validation_unopened": metrics.get("research_validation_opened") is False,
        "holdout_unopened": metrics.get("research_holdout_opened") is False,
        "run_ids": row.get("run_ids") == [],
        "true_authorities": all(validation.get(name) is True for name in TRUE_AUTHORITIES),
        "false_authorities": all(validation.get(name) is False for name in FALSE_AUTHORITIES),
        "self_path": validation.get("reviewed_comparator_path") == self_path.relative_to(ROOT).as_posix(),
        "self_sha": validation.get("reviewed_comparator_sha256") == sha_file(self_path),
        "hyp010_path": validation.get("reviewed_hyp010_comparator_path")
        == HYP010_COMPARATOR.relative_to(ROOT).as_posix(),
        "hyp010_sha": validation.get("reviewed_hyp010_comparator_sha256") == HYP010_COMPARATOR_SHA256,
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
        and validation.get("hyp010_terminal_row_sha256") == PARENT_TERMINAL_ROW_SHA256,
        "summary": validation.get("frozen_summary_sha256") == SUMMARY_SHA256,
        "nonfuture": issued <= datetime.now(timezone.utc),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"HYP011 comparator authority failed: {failed}")
    review_text = REVIEW.read_text(encoding="utf-8", errors="strict")
    if not review_text.startswith("# HYP011 pre-comparator independent review\n\nVerdict: `PASS_PRE_COMPARATOR`\n"):
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
    return {
        "registry_sha256": sha_bytes(registry_raw),
        "latest_row_sha256": sha_bytes(raw),
        "hyp010_terminal_row_sha256": sha_bytes(parent_raw),
    }, bindings


def recovered_validate_run(
    hyp010: types.ModuleType,
    base: types.ModuleType,
    parent_recovery: Callable[..., Any] | None = None,
):
    original_read_text = Path.read_text
    original_recovery: Callable[..., Any] = parent_recovery or hyp010.recovered_validate_run

    def exact_path_read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if path.resolve() == SUMMARY.resolve():
            encoding = kwargs.get("encoding", args[0] if args else None)
            if encoding != "utf-8":
                raise ValueError("frozen parent requested an unexpected summary encoding")
            text, _ = decode_exact_bom_json(path)
            return text
        return original_read_text(path, *args, **kwargs)

    Path.read_text = exact_path_read_text
    try:
        return original_recovery(base)
    finally:
        Path.read_text = original_read_text


def build_report(hyp010: types.ModuleType, base: types.ModuleType):
    original = hyp010.recovered_validate_run
    hyp010.recovered_validate_run = lambda module: recovered_validate_run(
        hyp010, module, original
    )
    try:
        report, bindings = hyp010.build_report(base)
    finally:
        hyp010.recovered_validate_run = original
    report = dict(report)
    report["schema_version"] = "stbs011_summary_bom_comparator_report.v1"
    report["hypothesis_id"] = HYPOTHESIS
    report["verdict"] = PASS_VERDICT
    report["summary_decoder"] = "EXACT_ONE_LEADING_UTF8_BOM_STRICT_UTF8_SINGLE_JSON_DOCUMENT"
    report["summary_sha256"] = SUMMARY_SHA256
    return report, bindings


def bind_inherited_inputs(
    hyp010: types.ModuleType,
    bindings: list[dict[str, str]],
) -> None:
    by_path = {Path(item["path"]).resolve(): item for item in bindings}
    for label, (path, expected) in hyp010.PARENT_BINDINGS.items():
        path = Path(path).resolve()
        inherited = require_file(path, expected, f"hyp010_{label}")
        prior = by_path.get(path)
        if prior is not None:
            if prior["sha256"] != inherited["sha256"]:
                raise ValueError(f"conflicting inherited binding for {path}")
            continue
        bindings.append(inherited)
        by_path[path] = inherited


def execute(registry: Path) -> dict[str, Any]:
    marker = claim(registry)
    terminal = OUTPUT_ROOT / "attempt_terminal.json"
    try:
        authority, bindings = validate_authority_after_claim(registry.resolve())
        hyp010 = load_hyp010()
        bind_inherited_inputs(hyp010, bindings)
        base = hyp010.load_parent_runner()
        first, first_extra = build_report(hyp010, base)
        second, second_extra = build_report(hyp010, base)
        report_raw = json_bytes(first)
        if report_raw != json_bytes(second) or first_extra != second_extra:
            raise ValueError("full HYP011 golden-path replay is not byte deterministic")
        for item in bindings + first_extra:
            if sha_file(Path(item["path"])) != item["sha256"]:
                raise ValueError(f"bound input changed before receipt: {item['label']}")
        report_path = OUTPUT_ROOT / "stbs011_summary_bom_comparator_report.json"
        write_exclusive(report_path, report_raw)
        receipt = {
            "schema_version": "stbs011_summary_bom_comparator_receipt.v1",
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
        receipt_path = OUTPUT_ROOT / "stbs011_summary_bom_comparator_receipt.json"
        write_exclusive(receipt_path, receipt_raw)
        write_exclusive(terminal, json_bytes({
            "schema_version": "stbs011_summary_bom_comparator_terminal.v1",
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
                "schema_version": "stbs011_summary_bom_comparator_terminal.v1",
                "hypothesis_id": HYPOTHESIS,
                "attempt_id": ATTEMPT,
                "status": "FAILED",
                "verdict": "STBS011_COMPARATOR_FAILED_CONSUMED",
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
