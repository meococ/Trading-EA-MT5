#!/usr/bin/env python3
"""Park outcome-blind HYP-002 and open the identity-only HYP-003 successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


EA_NAME = "EA_VRAS_RegimeAdaptiveScalperV4"
HYP002 = "HYP-VRAS-USDJPY-M5-002"
HYP003 = "HYP-VRAS-USDJPY-M5-003"
SOURCE_REL = f"03. EA Developer/{EA_NAME}/{EA_NAME}.mq5"
SNAPSHOT_REL = (
    f"03. EA Developer/{EA_NAME}/research/source_snapshots/"
    f"{EA_NAME}_HYP-VRAS-USDJPY-M5-002_8BC25B18.mq5"
)
HYP002_SOURCE_SHA = "8BC25B180E0C26AD6C5867F4F7ABEF4690EF00A41BE376B5408D82750DDE853A"
DATA_FINGERPRINT = "FFD3024F94509DCC5281F6956A237BED542F9161F44837BF2AAE904D76D9B695"
OVERRIDES = (
    "InpAtrPeriod=14;InpCommissionPips=0.70;InpCostDistanceMultiple=3.0;"
    "InpDailyHardStopPct=3.5;InpDailySoftStopPct=2.0;InpDirectionMultiplier=1;"
    "InpEnableTelemetry=true;InpEntryZ=2.0;InpExitAbsZ=0.25;"
    "InpHypothesisId=HYP-VRAS-USDJPY-M5-003;InpMagic=5601603;"
    "InpMaxAccountDrawdownPct=8.0;InpMaxHalfLifeBars=36.0;InpMaxHoldBars=18;"
    "InpMaxSpreadPips=1.20;InpMaxTradesPerDay=3;InpMaxVarianceRatio=1.0;"
    "InpMinHalfLifeBars=1.0;InpMinRewardRisk=1.5;InpMinStopAtr=1.5;"
    "InpOuWindow=72;InpResearchAutoMode=true;InpRiskPercent=0.25;"
    "InpSlippageOneWayPips=0.30;InpTailStopZ=4.0;InpVarianceRatioQ=5"
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def compact(row: dict[str, Any]) -> str:
    return json.dumps(row, separators=(",", ":"), ensure_ascii=False)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    package = root / "03. EA Developer" / EA_NAME
    research = package / "research"
    source = root / SOURCE_REL
    snapshot = root / SNAPSHOT_REL
    prereg = research / f"{HYP003}_FROZEN_PREREG.md"
    closeout = research / f"{HYP002}_OPERATIONAL_CLOSEOUT.json"
    old_cost = research / "preflight" / HYP002 / "cost_source_manifest.json"
    new_cost = research / "preflight" / HYP003 / "cost_source_manifest.json"
    audit = research / "evidence" / HYP003 / "NONREPAINT_AUDIT.json"
    compile_log = package / f"{EA_NAME}.log"
    ex5 = package / f"{EA_NAME}.ex5"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    validator = registry.with_name("validate_candidate_registry.py")
    required = (source, snapshot, prereg, closeout, old_cost, audit, compile_log, ex5)
    for path in required:
        if not path.is_file():
            raise ValueError(f"required successor artifact is missing: {path}")
    if sha256_file(snapshot) != HYP002_SOURCE_SHA:
        raise ValueError("HYP-002 source snapshot hash mismatch")

    source_hash = sha256_file(source)
    prereg_hash = sha256_file(prereg)
    closeout_hash = sha256_file(closeout)
    audit_hash = sha256_file(audit)
    compile_hash = sha256_file(compile_log)
    ex5_hash = sha256_file(ex5)

    cost = json.loads(old_cost.read_text(encoding="utf-8"))
    cost["data_fingerprint"] = DATA_FINGERPRINT
    write_json(new_cost, cost)
    cost_hash = sha256_file(new_cost)

    lines = registry.read_text(encoding="utf-8-sig").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    hyp002_rows = [row for row in rows if row.get("hypothesis_id") == HYP002]
    if not hyp002_rows or hyp002_rows[-1].get("state") != "screened":
        raise ValueError("latest HYP-002 registry state must be screened")
    if any(row.get("hypothesis_id") == HYP003 for row in rows):
        raise ValueError("HYP-003 already exists in the registry")

    parked = deepcopy(hyp002_rows[-1])
    parked["state"] = "parked"
    parked["verdict"] = "PARK_PRE_OUTCOME_DATA_FINGERPRINT_MISMATCH"
    parked["reason"] = (
        "The sole authorized Model 0 launch completed, but the report identity was "
        "100%/88937 bars/47662758 ticks instead of the preregistered foundation proxy. "
        "The run stopped before PF, PnL, DD, trade count, yearly result or validation access."
    )
    parked["updated_at_utc"] = "2026-08-02T16:05:00Z"
    parked["run_ids"] = ["20260802_224144"]
    parked["metrics"] = {
        **parked.get("metrics", {}),
        "mt5_launches": 1,
        "model0_runs_completed": 1,
        "performance_outcome_reads": 0,
        "economic_trials_consumed": 0,
        "economics_executed": False,
    }
    parked["validation"] = {
        **parked.get("validation", {}),
        "probe_status": "PARKED_PRE_OUTCOME_DATA_FINGERPRINT_MISMATCH",
        "model0_authorized": False,
        "research_falsification_authorized": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "optimization_authorized": False,
        "promotion_eligible": False,
        "validation_access_authorized": False,
        "holdout_access_authorized": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "market_edge_claim_authorized": False,
        "operational_closeout_path": closeout.relative_to(root).as_posix(),
        "operational_closeout_sha256": closeout_hash,
        "run_manifest_path": (
            f"02. AlphaFactory/runs/{EA_NAME}/20260802_224144/run_manifest.json"
        ),
        "run_manifest_sha256": "7F2F9C005DC511BD61651CA9DF9C1AA6872A046EEBA7D9E2711794186B1372AE",
        "report_path": f"02. AlphaFactory/runs/{EA_NAME}/20260802_224144/report.html",
        "report_sha256": "EED69A871A4D88028A4F18B3EDA3B7696ECF5A5EBDAB08C3347218EF8C82FCB8",
        "expected_data_fingerprint": "5275CC6187E49112F54F587A68EB3A79681450CA8F511EC88F5259ECAB5D503A",
        "actual_data_fingerprint": DATA_FINGERPRINT,
        "performance_outcome_read": False,
        "source_snapshot_path": SNAPSHOT_REL,
        "source_snapshot_sha256": HYP002_SOURCE_SHA,
        "failure_radius": "Report data identity only; no strategy or economic result was accessed.",
    }

    screened = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": HYP003,
        "ea_name": EA_NAME,
        "state": "screened",
        "parent_candidate": HYP002,
        "feature_family": "usdjpy-m5-asian-session-closed-bar-ou-mean-reversion-research-cost-proxy",
        "lane": "VRAS-USDJPY-M5-ASIAN-OU-HYP003-IDENTITY-CORRECTED",
        "symbol": "USDJPY",
        "timeframe": "M5",
        "window": {"from": "2016.01.04", "to": "2020.12.31"},
        "model": 0,
        "source_provenance": (
            "Fresh outcome-blind operational successor to HYP-002. Only embedded ID, magic "
            "and the observed report data fingerprint change; all strategy, risk, cost, window "
            "and acceptance fields remain frozen."
        ),
        "source_path": SOURCE_REL,
        "source_hash": source_hash,
        "prereg_path": prereg.relative_to(root).as_posix(),
        "prereg_sha256": prereg_hash,
        "exact_overrides": OVERRIDES,
        "evidence_contract_kind": "economic",
        "acceptance_contract": deepcopy(hyp002_rows[-1]["acceptance_contract"]),
        "verdict": "SCREENED_RESEARCH_PROXY_MODEL0_IDENTITY_CORRECTED_NON_PROMOTABLE",
        "reason": (
            "The HYP-002 report established only the non-economic dataset identity. One fresh "
            "primary Model 0 control is authorized under the corrected fingerprint; every "
            "research-proxy promotion restriction remains in force."
        ),
        "updated_at_utc": "2026-08-02T16:05:01Z",
        "run_ids": [],
        "metrics": {
            "inherited_p0_sessions": 1286,
            "contract_tests_passed": 33,
            "compile_errors": 0,
            "compile_warnings": 0,
            "ex5_bytes": ex5.stat().st_size,
            "predecessor_model0_runs": 1,
            "predecessor_performance_outcome_reads": 0,
            "mt5_launches": 0,
            "economic_trials_consumed": 0,
            "economics_executed": False,
        },
        "validation": {
            "probe_status": "SCREENED_RESEARCH_PROXY_MODEL0_IDENTITY_CORRECTED",
            "source_build_authorized": False,
            "model0_authorized": True,
            "research_falsification_authorized": True,
            "performance_metrics_authorized": True,
            "economic_validity_authorized": False,
            "optimization_authorized": False,
            "promotion_eligible": False,
            "validation_access_authorized": False,
            "holdout_access_authorized": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
            "market_edge_claim_authorized": False,
            "cost_status": "VERIFIED_RESEARCH_PROXY_NON_PROMOTION",
            "cost_source_manifest_path": new_cost.relative_to(root).as_posix(),
            "cost_source_manifest_sha256": cost_hash,
            "compile_log_path": compile_log.relative_to(root).as_posix(),
            "compile_log_sha256": compile_hash,
            "ex5_sha256": ex5_hash,
            "nonrepaint_status": "PASS",
            "nonrepaint_audit_path": audit.relative_to(root).as_posix(),
            "nonrepaint_audit_sha256": audit_hash,
            "identity_fingerprint_basis": {
                "broker": "Five Percent Online Ltd",
                "server": "FivePercentOnline-Real (Build 6090)",
                "currency": "USD",
                "initial_deposit": "10 000.00",
                "leverage": "1:100",
                "history_quality": "100%",
                "bars": "88937",
                "ticks": "47662758",
                "digits": 3,
                "point": 0.001,
                "pip_size": 0.01,
            },
            "identity_fingerprint": DATA_FINGERPRINT,
            "predecessor_closeout_path": closeout.relative_to(root).as_posix(),
            "predecessor_closeout_sha256": closeout_hash,
            "promotion_blocker": (
                "Commission is Strategy Tester simulation and quote-latency evidence has no "
                "observed fill; promotion-grade commission/slippage remain absent."
            ),
        },
    }
    row_path = research / f"{HYP003}_SCREENED_ROW.json"
    write_json(row_path, screened)
    payload = ("\n".join(lines + [compact(parked), compact(screened)]) + "\n").encode("utf-8")
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
    print(json.dumps({
        "status": "APPLIED" if args.apply else "STAGED_PASS",
        "hyp002_state": "parked",
        "hyp003_state": "screened",
        "hyp003_source_sha256": source_hash,
        "hyp003_prereg_sha256": prereg_hash,
        "hyp003_cost_manifest_sha256": cost_hash,
        "hyp003_data_fingerprint": DATA_FINGERPRINT,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
