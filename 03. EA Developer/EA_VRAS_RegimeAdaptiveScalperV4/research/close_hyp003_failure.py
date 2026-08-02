#!/usr/bin/env python3
"""Append the terminal HYP-003 economic/telemetry kill after validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path


HYPOTHESIS_ID = "HYP-VRAS-USDJPY-M5-003"
RUN_ID = "20260802_225843"
SOURCE_SHA = "B98AF548920E06D0FF6A0F9D12C601E9F5366DCAE057B0B766611FBE170E8EBA"
SNAPSHOT_REL = (
    "03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/research/source_snapshots/"
    "EA_VRAS_RegimeAdaptiveScalperV4_HYP-VRAS-USDJPY-M5-003_B98AF548.mq5"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repair-latest", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    validator = registry.with_name("validate_candidate_registry.py")
    packet = Path(__file__).with_name(f"{HYPOTHESIS_ID}_FAILURE_PACKET.json")
    snapshot = root / SNAPSHOT_REL
    package = root / "03. EA Developer" / "EA_VRAS_RegimeAdaptiveScalperV4"
    compile_log = package / "EA_VRAS_RegimeAdaptiveScalperV4.log"
    canonical_ex5 = package / "EA_VRAS_RegimeAdaptiveScalperV4.ex5"
    run_root = root / "02. AlphaFactory" / "runs" / "EA_VRAS_RegimeAdaptiveScalperV4" / RUN_ID
    evidence_root = (
        package / "research" / "evidence" / HYPOTHESIS_ID / "MODEL0_PRIMARY"
    )
    artifacts = {
        "failure_packet_sha256": sha256_file(packet),
        "run_manifest_sha256": sha256_file(evidence_root / "run_manifest.json"),
        "report_sha256": sha256_file(evidence_root / "report.html"),
        "enhanced_summary_sha256": sha256_file(evidence_root / "enhanced_summary.json"),
        "nonrepaint_audit_sha256": sha256_file(evidence_root / "nonrepaint_audit.json"),
        "lifecycle_sha256": sha256_file(evidence_root / "USDJPY_LifecycleTrades_HYP-VRAS-USDJPY-M5-003_53343921.csv"),
        "run_meta_sha256": sha256_file(evidence_root / "USDJPY_RunMeta_HYP-VRAS-USDJPY-M5-003_53343921.json"),
    }
    mirrors = {
        evidence_root / "run_manifest.json": run_root / "run_manifest.json",
        evidence_root / "report.html": run_root / "report.html",
        evidence_root / "enhanced_summary.json": run_root / "analysis" / "enhanced_summary.json",
        evidence_root / "nonrepaint_audit.json": run_root / "analysis" / "nonrepaint_audit.json",
        evidence_root / "USDJPY_LifecycleTrades_HYP-VRAS-USDJPY-M5-003_53343921.csv": run_root / "logs" / "USDJPY_LifecycleTrades_HYP-VRAS-USDJPY-M5-003_53343921.csv",
        evidence_root / "USDJPY_RunMeta_HYP-VRAS-USDJPY-M5-003_53343921.json": run_root / "logs" / "USDJPY_RunMeta_HYP-VRAS-USDJPY-M5-003_53343921.json",
    }
    for mirror, original in mirrors.items():
        if sha256_file(mirror) != sha256_file(original):
            raise ValueError(f"durable evidence mirror drifted from run artifact: {mirror}")
    durable_ex5 = evidence_root / "EA_VRAS_RegimeAdaptiveScalperV4.ex5.bin"
    if sha256_file(durable_ex5) != sha256_file(canonical_ex5):
        raise ValueError("durable EX5 mirror drifted from the final compile output")
    expected = json.loads(packet.read_text(encoding="utf-8"))
    if expected["run_identity"]["run_manifest_sha256"] != artifacts["run_manifest_sha256"]:
        raise ValueError("failure packet run manifest hash mismatch")
    if expected["run_identity"]["report_sha256"] != artifacts["report_sha256"]:
        raise ValueError("failure packet report hash mismatch")
    if sha256_file(snapshot) != SOURCE_SHA:
        raise ValueError("HYP-003 source snapshot hash mismatch")

    lines = registry.read_text(encoding="utf-8-sig").splitlines()
    matches = [json.loads(line) for line in lines if json.loads(line).get("hypothesis_id") == HYPOTHESIS_ID]
    if not matches:
        raise ValueError("HYP-003 is absent from the registry")
    if matches[-1].get("state") == "screened" and not args.repair_latest:
        base = matches[-1]
    elif (
        args.repair_latest
        and matches[-1].get("state") == "killed"
        and len(matches) >= 2
        and matches[-2].get("state") == "screened"
    ):
        base = matches[-2]
    else:
        raise ValueError("latest HYP-003 row is outside the append/repair contract")
    row = deepcopy(base)
    row["state"] = "killed"
    row["verdict"] = "KILL_PRIMARY_MODEL0_ZERO_EDGE_AND_CADENCE_TELEMETRY_CONTRACT_FAIL"
    row["reason"] = (
        "The sole primary Model 0 run produced 3/3 losses, PF 0.0, net -47.75 USD and "
        "0.0115 trades/elapsed week. Lifecycle final-close rows also carried zero volume/epoch "
        "time, blocking report-bound cost repricing. Primary PF/cadence already make the kill terminal."
    )
    row["updated_at_utc"] = "2026-08-02T16:15:00Z"
    row["run_ids"] = [RUN_ID]
    row["metrics"] = {
        **row.get("metrics", {}),
        "mt5_launches": 1,
        "model0_runs_completed": 1,
        "economic_trials_consumed": 1,
        "trades_executed": 3,
        "ex5_bytes": canonical_ex5.stat().st_size,
        "trades_per_elapsed_week": 0.011513157894736843,
        "net_profit_usd": -47.75,
        "profit_factor": 0.0,
        "win_rate_pct": 0.0,
        "expectancy_usd_per_trade": -15.916666666666666,
        "max_drawdown_pct": 0.2336710921492076,
        "economics_executed": True,
    }
    row["validation"] = {
        **row.get("validation", {}),
        "probe_status": "KILLED_PRIMARY_MODEL0_ZERO_EDGE_AND_CADENCE",
        "model0_authorized": False,
        "research_falsification_authorized": False,
        "performance_metrics_authorized": False,
        "economic_validity_authorized": False,
        "economics_authorized": False,
        "optimization_authorized": False,
        "promotion_eligible": False,
        "validation_access_authorized": False,
        "holdout_access_authorized": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "market_edge_claim_authorized": False,
        "failure_packet_path": packet.relative_to(root).as_posix(),
        "failure_packet_sha256": artifacts["failure_packet_sha256"],
        "run_manifest_path": (evidence_root / "run_manifest.json").relative_to(root).as_posix(),
        "run_manifest_sha256": artifacts["run_manifest_sha256"],
        "report_path": (evidence_root / "report.html").relative_to(root).as_posix(),
        "report_sha256": artifacts["report_sha256"],
        "enhanced_summary_path": (evidence_root / "enhanced_summary.json").relative_to(root).as_posix(),
        "enhanced_summary_sha256": artifacts["enhanced_summary_sha256"],
        "nonrepaint_audit_path": (evidence_root / "nonrepaint_audit.json").relative_to(root).as_posix(),
        "nonrepaint_audit_sha256": artifacts["nonrepaint_audit_sha256"],
        "lifecycle_path": (evidence_root / "USDJPY_LifecycleTrades_HYP-VRAS-USDJPY-M5-003_53343921.csv").relative_to(root).as_posix(),
        "lifecycle_sha256": artifacts["lifecycle_sha256"],
        "run_meta_path": (evidence_root / "USDJPY_RunMeta_HYP-VRAS-USDJPY-M5-003_53343921.json").relative_to(root).as_posix(),
        "run_meta_sha256": artifacts["run_meta_sha256"],
        "verified_cost_artifact_status": "NOT_CREATED_LIFECYCLE_ZERO_VOLUME",
        "unified_validation_status": "NOT_COMPLETED_AFTER_PRIMARY_KILL",
        "source_snapshot_path": SNAPSHOT_REL,
        "source_snapshot_sha256": SOURCE_SHA,
        "compile_log_path": (evidence_root / "FINAL_COMPILE_LOG.txt").relative_to(root).as_posix(),
        "compile_log_sha256": sha256_file(evidence_root / "FINAL_COMPILE_LOG.txt"),
        "ex5_path": durable_ex5.relative_to(root).as_posix(),
        "ex5_sha256": sha256_file(durable_ex5),
        "failure_radius": expected["failure_radius"],
    }
    row_path = Path(__file__).with_name(f"{HYPOTHESIS_ID}_KILLED_ROW.json")
    row_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    compact_row = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
    if args.repair_latest:
        if json.loads(lines[-1]).get("hypothesis_id") != HYPOTHESIS_ID:
            raise ValueError("repair requires HYP-003 to be the last registry row")
        output_lines = lines[:-1] + [compact_row]
    else:
        output_lines = lines + [compact_row]
    payload = ("\n".join(output_lines) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".jsonl", delete=False) as handle:
        staged = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        subprocess.run(["python", str(validator), "--registry", str(staged)], cwd=root, check=True)
        if args.apply:
            temporary = registry.with_name(f".{registry.name}.{os.getpid()}.tmp")
            temporary.write_bytes(payload)
            temporary.replace(registry)
            subprocess.run(["python", str(validator)], cwd=root, check=True)
    finally:
        staged.unlink(missing_ok=True)
    print(json.dumps({"status": "APPLIED" if args.apply else "STAGED_PASS", "row": row}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
