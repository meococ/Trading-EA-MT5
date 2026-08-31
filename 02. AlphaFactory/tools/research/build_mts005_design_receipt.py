"""Build hash-bound AlphaFactory DESIGN receipts for MTS005."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROFILE = "mts005"
HYPOTHESIS_ID = "HYP-MULTI-TSMOM-D1-005"
EA_NAME = "EA_MultiAssetTSMOMD1V5"
SYMBOL = "AFD_EURUSD_DUKA_TSMOM_V5"
PRIMARY_MAGIC = 260812007
COMPARATOR_MAGIC = 260812008
PERIOD = "H1"
FROM_DATE = "2018.01.01"
TO_DATE = "2022.01.01"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest().upper()


class ReceiptBuildError(RuntimeError):
    pass


def select_profile(profile: str) -> None:
    global PROFILE, HYPOTHESIS_ID, EA_NAME, SYMBOL, PRIMARY_MAGIC, COMPARATOR_MAGIC
    PROFILE = profile
    if profile == "mts006":
        HYPOTHESIS_ID = "HYP-MULTI-TSMOM-D1-006"
        EA_NAME = "EA_MultiAssetTSMOMD1V6"
        SYMBOL = "EURUSD_AFD_TSMOM_V6"
        PRIMARY_MAGIC = 260812009
        COMPARATOR_MAGIC = 260812010


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ReceiptBuildError(f"file not found: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tree_sha256(path: Path) -> str:
    if not path.is_dir():
        raise ReceiptBuildError(f"directory not found: {path}")
    records = [
        f"{item.relative_to(path).as_posix()}\t{sha256_file(item)}"
        for item in sorted((row for row in path.rglob("*") if row.is_file()), key=lambda row: row.as_posix())
    ]
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest().upper()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def git_snapshot(root: Path) -> tuple[str, list[str], str]:
    commit = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8", errors="strict").strip()
    raw = subprocess.run(
        ["git", "-C", str(root), "status", "--short", "--untracked-files=all"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8", errors="strict")
    lines = raw.splitlines()
    status_sha = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest().upper()
    return commit, lines, status_sha


def evidence(label: str, path: Path, *, kind: str = "file") -> dict[str, str]:
    digest = tree_sha256(path) if kind == "directory" else sha256_file(path)
    return {"label": label, "kind": kind, "path": str(path.resolve()), "sha256": digest}


def build(args: argparse.Namespace) -> int:
    root = args.repo_root.resolve()
    package = root / "03. EA Developer" / EA_NAME
    research = package / "research"
    role_name = args.role
    run_role = "control" if role_name == "primary" else "challenger"
    magic = PRIMARY_MAGIC if role_name == "primary" else COMPARATOR_MAGIC
    comparator = "false" if role_name == "primary" else "true"
    overrides = (
        f"InpDeviationPoints=20;InpLongOnlyComparator={comparator};"
        f"InpMagic={magic};InpResearchAutoMode=true"
    )
    preflight = research / "preflight" / HYPOTHESIS_ID / "DESIGN" / role_name
    task_path = preflight / "task_packet.json"
    cost_manifest_path = preflight / "cost_source_manifest.json"
    receipt_path = preflight / "contract_receipt.json"
    for placeholder in (task_path, cost_manifest_path, receipt_path):
        write_json(placeholder, {"status": "BUILD_PLACEHOLDER"})

    source = package / f"{EA_NAME}.mq5"
    prereg = research / f"{HYPOTHESIS_ID}_FROZEN_DESIGN_PREREG.md"
    source_contract = research / f"{HYPOTHESIS_ID}_JETTA_H1_SOURCE_CONTRACT.json"
    cost_contract = research / f"{HYPOTHESIS_ID}_COST_CONTRACT.json"
    source_validation = (
        research
        / "evidence"
        / "source_validation"
        / f"{HYPOTHESIS_ID}_SOURCE_VALIDATION.json"
    )
    import_receipts = research / "evidence" / "import"
    grok_checkpoint = research / f"{HYPOTHESIS_ID}_GROK_PRE_DESIGN_CHECKPOINT.md"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    nonrepaint = package / f"{HYPOTHESIS_ID}_NONREPAINT_MANIFEST.json"
    cost_evidence = research / f"{HYPOTHESIS_ID}_COST_EVIDENCE.json"

    source_selection: Path | None = None
    parent_failure: Path | None = None
    if PROFILE == "mts006":
        parent_research = root / "03. EA Developer" / "EA_MultiAssetTSMOMD1V5" / "research"
        source_contract = parent_research / "HYP-MULTI-TSMOM-D1-005_JETTA_H1_SOURCE_CONTRACT.json"
        source_validation = (
            parent_research
            / "evidence"
            / "source_validation"
            / "HYP-MULTI-TSMOM-D1-005_SOURCE_VALIDATION.json"
        )
        source_selection = research / f"{HYPOTHESIS_ID}_SOURCE_SELECTION_RECEIPT.json"
        parent_failure = parent_research / "HYP-MULTI-TSMOM-D1-005_SOURCE_FAILURE.md"
        grok_checkpoint = research / f"{HYPOTHESIS_ID}_GROK_DISCOVERY_FRONTIER.md"

    imports = sorted(import_receipts.glob("*_IMPORT_RUN.json"))
    expected_imports = 8 if PROFILE == "mts006" else 9
    if len(imports) != expected_imports:
        raise ReceiptBuildError(f"expected {expected_imports} MT5 import receipts, got {len(imports)}")
    for path in imports:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS_SOURCE_IMPORT":
            raise ReceiptBuildError(f"MT5 import did not pass: {path}")
    validation_payload = json.loads(source_validation.read_text(encoding="utf-8"))
    if PROFILE == "mts006":
        if source_selection is None:
            raise ReceiptBuildError("MTS006 source selection path missing")
        selection_payload = json.loads(source_selection.read_text(encoding="utf-8"))
        if selection_payload.get("status") != "PASS_SELECTED_EIGHT_SYMBOL_SOURCE_ONLY":
            raise ReceiptBuildError("MTS006 source selection is not PASS")
    elif validation_payload.get("status") != "PASS":
        raise ReceiptBuildError("source validation is not PASS")

    cost_manifest: dict[str, object] = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "symbol": SYMBOL,
        "broker": "Five Percent Online portable MT5 contract proxies",
        "server": "AlphaFactory portable FivePercent lane with Dukascopy Jetta custom symbols",
        "spread_source": "Contemporaneous Jetta H1 ASK-open minus BID-open, stored in MT5 custom rates",
        "commission_source": "Official The5ers formula plus same-terminal XAU/BTC commissioned-deal receipts",
        "swap_source": "Controlled current-broker adverse financing floor overlay; native signed swap removed",
        "slippage_source": "Frozen 0.25/0.50/1.00 contemporaneous one-spread USD cost per deal",
        "cost_contract_path": str(cost_contract.resolve()),
        "cost_contract_sha256": sha256_file(cost_contract),
        "source_contract_path": str(source_contract.resolve()),
        "source_contract_sha256": sha256_file(source_contract),
        "source_validation_sha256": sha256_file(source_validation),
        "mt5_import_receipts_tree_sha256": tree_sha256(import_receipts),
        "status": "FROZEN_PRE_ECONOMIC_CONTROLLED_COSTS",
        "economic_claim_authorized": False,
    }
    if source_selection is not None:
        cost_manifest["source_selection_path"] = str(source_selection.resolve())
        cost_manifest["source_selection_sha256"] = sha256_file(source_selection)
    write_json(cost_manifest_path, cost_manifest)

    # Paths are now stable in git status. Rewriting their contents does not
    # alter the porcelain status list, avoiding receipt/status circularity.
    git_commit, git_status, git_status_sha = git_snapshot(root)
    asof = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat(timespec="seconds").replace("+00:00", "Z")
    data_quality = {
        "availability_asof_utc": asof,
        "coverage_mode": "fixed_window",
        "history_quality": {"operator": "gt", "value": 97},
        "requested_from": FROM_DATE,
        "requested_to": TO_DATE,
        "require_tester_journal_bounds": True,
        "max_journal_delta_bytes": 16777216,
    }
    task: dict[str, object] = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": run_role,
        "strategy_role": "primary_design_baseline" if role_name == "primary" else "frozen_long_only_comparator",
        "ea_name": EA_NAME,
        "source_path": source.relative_to(root).as_posix(),
        "source_sha256": sha256_file(source),
        "registry_path": registry.relative_to(root).as_posix(),
        "registry_sha256": sha256_file(registry),
        "registry_row_sha256": sha256_file(registry),
        "prereg_path": prereg.relative_to(root).as_posix(),
        "prereg_sha256": sha256_file(prereg),
        "ea_contract_path": ea_contract.relative_to(root).as_posix(),
        "ea_contract_sha256": sha256_file(ea_contract),
        "telemetry_profile": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "symbol": SYMBOL,
        "period": PERIOD,
        "from": FROM_DATE,
        "to": TO_DATE,
        "data_quality_contract": data_quality,
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "timeout_sec": 3600,
        "overrides": overrides,
        "telemetry_tier": "off",
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "visual_mode": False,
        "indicator_dependencies": [],
        "validation_stage": "design",
        "holding_contract": "weekly_rebalance",
        "holdout_access_authorized": False,
        "optimization_authorized": False,
        "promotion_eligible": False,
        "git_commit": git_commit,
        "git_status": git_status,
        "git_status_sha256": git_status_sha,
        "include_closure": [],
        "include_closure_sha256": EMPTY_SHA256,
        "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
        "required_sidecars": [],
        "cost_source_manifest_path": cost_manifest_path.relative_to(root).as_posix(),
        "cost_source_manifest_sha256": sha256_file(cost_manifest_path),
    }
    matched_evidence: list[dict[str, str]] = []
    if role_name == "comparator":
        if args.matched_control_manifest is None or args.matched_control_report is None:
            raise ReceiptBuildError("comparator requires matched control manifest and report")
        manifest_path = args.matched_control_manifest.resolve()
        report_path = args.matched_control_report.resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        task.update(
            {
                "matched_control_run_id": str(manifest["run_id"]),
                "matched_control_hypothesis_id": str(manifest["hypothesis_id"]),
                "matched_control_manifest_sha256": sha256_file(manifest_path),
                "matched_control_report_sha256": sha256_file(report_path),
                "matched_control_overrides": str(manifest["overrides"]),
                "matched_control_source_sha256": str(manifest["source_sha256"]),
                "matched_control_config_sha256": str(manifest["config_sha256"]),
                "matched_control_ex5_sha256": str(manifest["ex5_sha256"]),
                "matched_control_includes_sha256": str(manifest["includes_sha256"]),
                "matched_control_git_commit": str(manifest["git_commit"]),
                "matched_control_git_status_sha256": str(manifest["git_status_sha256"]),
            }
        )
        matched_evidence = [
            evidence("matched_control_manifest", manifest_path),
            evidence("matched_control_report", report_path),
        ]
    write_json(task_path, task)

    binding = {
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": run_role,
        "ea_name": EA_NAME,
        "symbol": SYMBOL,
        "period": PERIOD,
        "from": FROM_DATE,
        "to": TO_DATE,
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "timeout_sec": 3600,
        "overrides": overrides,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 100000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": [],
        "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
        "visual_mode": False,
        "indicator_dependencies": [],
        "include_closure_sha256": EMPTY_SHA256,
        "data_quality_contract": data_quality,
    }
    receipt_evidence = [
        evidence("task_packet", task_path),
        evidence("source", source),
        evidence("prereg", prereg),
        evidence("cost_source_manifest", cost_manifest_path),
        evidence("candidate_registry", registry),
        evidence("ea_contract", ea_contract),
        evidence("nonrepaint_audit", nonrepaint),
        evidence("source_contract", source_contract),
        evidence("cost_contract", cost_contract),
        evidence("source_validation", source_validation),
        evidence("source_import_receipts", import_receipts, kind="directory"),
        evidence("grok_pre_design_checkpoint", grok_checkpoint),
        *matched_evidence,
    ]
    if PROFILE == "mts005":
        receipt_evidence.append(evidence("cost_evidence", cost_evidence))
    else:
        assert source_selection is not None and parent_failure is not None
        receipt_evidence.extend(
            [
                evidence("source_selection", source_selection),
                evidence("parent_source_failure", parent_failure),
            ]
        )
    receipt: dict[str, object] = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "task_packet_sha256": sha256_file(task_path),
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": binding,
        "evidence": receipt_evidence,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "note": f"Frozen {PROFILE.upper()} DESIGN arm; no validation, holdout, optimization or promotion authority.",
    }
    write_json(receipt_path, receipt)
    payload = {
        "status": "PASS_RECEIPT_BUILD",
        "role": role_name,
        "task_packet": str(task_path.resolve()),
        "task_packet_sha256": sha256_file(task_path),
        "contract_receipt": str(receipt_path.resolve()),
        "contract_receipt_sha256": sha256_file(receipt_path),
        "overrides": overrides,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build MTS005 DESIGN AlphaFactory receipt")
    parser.add_argument("--profile", choices=("mts005", "mts006"), default="mts005")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--role", choices=("primary", "comparator"), required=True)
    parser.add_argument("--matched-control-manifest", type=Path)
    parser.add_argument("--matched-control-report", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        select_profile(args.profile)
        return build(args)
    except (ReceiptBuildError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FATAL {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
