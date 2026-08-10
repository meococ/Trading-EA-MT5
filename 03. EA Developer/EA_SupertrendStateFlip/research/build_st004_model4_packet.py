#!/usr/bin/env python3
"""Build the frozen zero-trade Model-4 packet and non-repaint manifest for HYP008."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-008"
PARENT_HYPOTHESIS_ID = "HYP-ST-XAUUSD-H1-007"
EA_NAME = "EA_SupertrendStateFlip"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
AUDIT_RUN_ID = "ST008-MQL5-STATIC-001"
FROM = "2005.01.01"
TO = "2023.01.01"
ASOF = "2026-08-08T22:15:00Z"
OVERRIDES = (
    "InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;"
    "InpParityFileName=ST003_MQL5_PARITY_001.csv"
)
SOURCE_SHA256 = "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF"
PARENT_SOURCE_SHA256 = "C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02"
ALPHA_PS1_SHA256 = "68BCF4A4F8CF8990A830142F37CDD25C05B665C6BDA02A85DF042BD6DED385E8"
QUANT_ANALYZER_SHA256 = "A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B"
NONREPAINT_TOOL_SHA256 = "366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def git_lines(*args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("utf-8").splitlines()


def file_evidence(label: str, path: Path) -> dict[str, str]:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or sha256_file(path) != expected:
        raise ValueError(f"{label} is absent or changed: {path}")


def latest_hyp007_row(registry: Path) -> tuple[bytes, dict[str, Any]]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == PARENT_HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("canonical registry has no HYP007 row")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "killed",
        "verdict": row.get("verdict") == "KILL_MT5_PREHISTORY_UNAVAILABLE_AND_LOCALIZED_HQ_PARSE",
        "source": row.get("source_hash") == PARENT_SOURCE_SHA256,
        "mt5_attempt": validation.get("mt5_parity_attempt_id") == "ST007-MT5-001",
        "mt5_limit": validation.get("mt5_parity_attempt_limit") == 1,
        "mt5_consumed": metrics.get("mt5_parity_attempts_consumed") == 1,
        "mt5_run": metrics.get("mt5_runs_executed") == 1,
        "no_common": validation.get("file_common_output_created") is False,
        "no_mt5": validation.get("mt5_parity_run_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"HYP007 terminal prehistory evidence mismatch: {failed}")
    return raw, row


def main() -> int:
    package = ROOT / "03. EA Developer/EA_SupertrendStateFlip"
    research = package / "research"
    preflight = research / "preflight/HYP-ST-XAUUSD-H1-008/V3"
    source = package / "EA_SupertrendStateFlip.mq5"
    prereg = research / "HYP-ST-XAUUSD-H1-008_MT5_PARITY_PREREG_V3.md"
    addendum = research / "HYP-ST-XAUUSD-H1-007_MT5_PREHISTORY_FAILURE.md"
    parent_attempt = research / "evidence/HYP-ST-XAUUSD-H1-007/ST007-MT5-001/attempt_started.json"
    parent_terminal = research / "evidence/HYP-ST-XAUUSD-H1-007/ST007-MT5-001/attempt_terminal.json"
    parent_stdout = research / "evidence/HYP-ST-XAUUSD-H1-007/ST007-MT5-001/alpha_stdout.log"
    parent_stderr = research / "evidence/HYP-ST-XAUUSD-H1-007/ST007-MT5-001/alpha_stderr.log"
    parent_manifest = ROOT / "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_060651/run_manifest.json"
    parent_report = ROOT / "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_060651/report.html"
    parent_journal = ROOT / "02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_060651/logs/tester_journal_delta.log"
    cost_manifest = research / "HYP008_COLLECTION_ONLY_COST_SOURCE_MANIFEST_V3.json"
    registry = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    registry_snapshot = preflight / "candidate_registry.pre_mt5.jsonl"
    packet_path = preflight / "task_packet.control.json"
    receipt_path = preflight / "contract_receipt.control.json"
    audit_path = research / "HYP-ST-XAUUSD-H1-008_V3_NONREPAINT_AUDIT.json"
    review_path = research / "HYP-ST-XAUUSD-H1-008_V3_PRE_MT5_REVIEW.md"
    manifest_path = package / "HYP-ST-XAUUSD-H1-008_V3_NONREPAINT_MANIFEST.json"
    launcher = research / "run_st004_mt5_parity.py"
    collector = research / "collect_st004_mt5_artifacts.py"
    comparator = research / "compare_st003_mql5_parity.py"
    tests = research / "tests/test_st004_mt5_artifacts.py"
    legacy_tests = research / "tests/test_st003_mql5_parity.py"
    alpha = ROOT / "02. AlphaFactory/alpha.ps1"
    quant = ROOT / "02. AlphaFactory/analysis/quant_analyzer.py"
    audit_tool = ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
    gitignore = ROOT / ".gitignore"

    require_hash(source, SOURCE_SHA256, "canonical source")
    require_hash(alpha, ALPHA_PS1_SHA256, "AlphaFactory")
    require_hash(quant, QUANT_ANALYZER_SHA256, "quant analyzer")
    require_hash(audit_tool, NONREPAINT_TOOL_SHA256, "non-repaint auditor")
    for required in (prereg, addendum, parent_attempt, parent_terminal, parent_stdout, parent_stderr, parent_manifest, parent_report, parent_journal, cost_manifest, registry, launcher, collector, comparator, tests, legacy_tests, gitignore):
        if not required.is_file():
            raise ValueError(f"required input is missing: {required}")
    raw_row, row = latest_hyp007_row(registry)
    if sha256_file(addendum) != "0E7A895A96CE42CCAD1A98E195C2E7A3D1610AC0CB5C818EB3AD8F8E1969AF2A":
        raise ValueError("HYP007 prehistory failure result changed before HYP008 packet build")
    require_hash(parent_attempt, "2CFFF47409753AC108BDCCCEF36DCA630404701FA2CA6794570F32D15528B473", "HYP007 attempt marker")
    require_hash(parent_terminal, "6003410F92D94B31695D322777A7896B4B75C3F6D7828A8C7AE09C31CBCBFFB8", "HYP007 attempt terminal")
    require_hash(parent_stdout, "FCC8A66C6AC9C3266E6171499DB5CC6EF316FC0F5DC7F46816E3B6583D0C54B0", "HYP007 AlphaFactory stdout")
    require_hash(parent_stderr, "422A431B8A79DBE2F0BAD5815E7254B9D35D7BE1E14C0DCF97022D82BF045A5C", "HYP007 AlphaFactory stderr")
    require_hash(parent_manifest, "BDD1C9A983532425C196F48C033BCFB30BE11FDC562D824CF88C8D9947666D35", "HYP007 run manifest")
    require_hash(parent_report, "C9A33DB3EFF771FF705FD41EEC316DF28FBD933C66F1C333BFA3945BFEFB4781", "HYP007 tester report")
    require_hash(parent_journal, "2A2380BA881FDBA5066A7A5E32A2F076E7882AA1E85D0240C908D26331A7AF68", "HYP007 journal")

    common = Path.home() / "AppData/Roaming/MetaQuotes/Terminal/Common/Files/ST003_MQL5_PARITY_001.csv"
    if common.exists():
        raise ValueError("frozen FILE_COMMON output already exists")
    attempt_probe = research / "evidence/HYP-ST-XAUUSD-H1-008/ST008-MT5-001/attempt_started.json"
    ignored = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", "--", str(attempt_probe.relative_to(ROOT))],
        check=False,
    )
    if ignored.returncode != 0:
        raise ValueError("one-shot MT5 evidence path is not excluded from the signed Git snapshot")

    preflight.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(registry, registry_snapshot)
    packet_path.touch()
    receipt_path.touch()
    audit_path.write_text("{}\n", encoding="utf-8")
    review_path.write_text("# HYP-ST-XAUUSD-H1-008 V3 - Independent pre-MT5 review\n\nStatus: `PENDING`\n", encoding="utf-8")
    manifest_path.touch(exist_ok=True)

    data_quality = {
        "history_quality": {"operator": "gt", "value": 97.0},
        "coverage_mode": "fixed_window",
        "availability_asof_utc": ASOF,
        "requested_from": FROM,
        "requested_to": TO,
        "require_tester_journal_bounds": True,
    }
    packet: dict[str, Any] = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_candidate": PARENT_HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "source_path": repo_path(source),
        "source_sha256": SOURCE_SHA256,
        "registry_path": repo_path(registry_snapshot),
        "registry_sha256": sha256_file(registry_snapshot),
        "registry_row_sha256": sha256_bytes(raw_row),
        "prereg_path": repo_path(prereg),
        "prereg_sha256": sha256_file(prereg),
        "telemetry_profile": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "symbol": "XAUUSD",
        "period": "H1",
        "from": FROM,
        "to": TO,
        "data_quality_contract": data_quality,
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": OVERRIDES,
        "telemetry_tier": "off",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "validation_stage": "source_feasibility",
        "holding_contract": "non_trading_collection",
        "include_closure": [],
        "include_closure_sha256": EMPTY_SHA256,
        "indicator_dependencies": [],
        "broker_fingerprint": None,
        "server_fingerprint": None,
        "account_fingerprint": None,
        "data_fingerprint": None,
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "required_sidecars": [],
        "required_manifest_hashes": [
            "source_sha256", "config_sha256", "report_sha256", "ex5_sha256", "includes_sha256"
        ],
        "cost_source_manifest_path": repo_path(cost_manifest),
        "cost_source_manifest_sha256": sha256_file(cost_manifest),
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    commit = git_lines("rev-parse", "HEAD")[0].strip()
    status = git_lines("status", "--short", "--untracked-files=all")
    status_sha = sha256_bytes("\n".join(status).encode("utf-8"))
    packet["git_commit"] = commit
    packet["git_status"] = status
    packet["git_status_sha256"] = status_sha
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    binding = {
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "H1",
        "from": FROM,
        "to": TO,
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": OVERRIDES,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": [],
        "indicator_dependencies": [],
        "broker_fingerprint": None,
        "server_fingerprint": None,
        "account_fingerprint": None,
        "data_fingerprint": None,
        "symbol_geometry": packet["symbol_geometry"],
        "include_closure_sha256": EMPTY_SHA256,
        "data_quality_contract": data_quality,
    }
    evidence = [
        file_evidence("task_packet", packet_path),
        file_evidence("candidate_registry", registry_snapshot),
        file_evidence("source", source),
        file_evidence("prereg", prereg),
        file_evidence("cost_source_manifest", cost_manifest),
        file_evidence("parent_launch_failure_result", addendum),
        file_evidence("parent_attempt_started", parent_attempt),
        file_evidence("parent_attempt_terminal", parent_terminal),
        file_evidence("parent_alpha_stdout", parent_stdout),
        file_evidence("parent_alpha_stderr", parent_stderr),
        file_evidence("parent_run_manifest", parent_manifest),
        file_evidence("parent_tester_report", parent_report),
        file_evidence("parent_tester_journal", parent_journal),
        file_evidence("gitignore_runtime_boundary", gitignore),
        file_evidence("mt5_launcher", launcher),
        file_evidence("artifact_collector", collector),
        file_evidence("comparator", comparator),
        file_evidence("hyp004_tests", tests),
        file_evidence("hyp003_tests", legacy_tests),
        file_evidence("alpha_ps1", alpha),
        file_evidence("quant_analyzer", quant),
        file_evidence("nonrepaint_tool", audit_tool),
    ]
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": AUTHORITY,
        "hypothesis_id": HYPOTHESIS_ID,
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": binding,
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "alphafactory_run_manifest.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": AUDIT_RUN_ID,
        "snapshot_root": str(package.resolve()),
        "source_snapshot": str(source.resolve()),
        "source_sha256": SOURCE_SHA256,
        "include_snapshots": [],
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "H1",
        "from": FROM,
        "to": TO,
        "model": 0,
        "run_role": "control",
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "telemetry_profile": "none",
        "telemetry_tier": "off",
        "broker_fingerprint": None,
        "server_fingerprint": None,
        "account_fingerprint": None,
        "data_fingerprint": None,
        "overrides": OVERRIDES,
        "required_sidecars": [],
        "contract_symbol_geometry": binding["symbol_geometry"],
        "includes_sha256": EMPTY_SHA256,
        "data_quality_contract": {
            "history_quality_threshold": 97.0,
            "coverage_mode": "fixed_window",
            "availability_asof_utc": ASOF,
            "requested_from": FROM,
            "requested_to": TO,
            "require_tester_journal_bounds": True,
        },
        "contract_receipt_sha256": sha256_file(receipt_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if git_lines("status", "--short", "--untracked-files=all") != status:
        raise ValueError("Git status changed while the packet/receipt/manifest were being sealed")
    print(json.dumps({
        "task_packet": packet_path.as_posix(),
        "task_packet_sha256": sha256_file(packet_path),
        "contract_receipt": receipt_path.as_posix(),
        "contract_receipt_sha256": sha256_file(receipt_path),
        "candidate_registry_snapshot_sha256": sha256_file(registry_snapshot),
        "nonrepaint_manifest": manifest_path.as_posix(),
        "nonrepaint_manifest_sha256": sha256_file(manifest_path),
        "git_commit": commit,
        "git_status_sha256": status_sha,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
