#!/usr/bin/env python3
"""Build the frozen HYP-003 identity-corrected research control packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-VRAS-USDJPY-M5-003"
EA_NAME = "EA_VRAS_RegimeAdaptiveScalperV4"
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
ACCEPTANCE = {
    "min_profit_factor": 1.3,
    "min_trades_per_week": 2.0,
    "max_trades_per_week": 5.0,
    "max_drawdown_pct": 8.0,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1.0,
    "max_monte_carlo_p95_dd_pct": 8.0,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def repo_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def git_output(root: Path, *args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("utf-8").splitlines()


def latest_registry_row(registry: Path) -> tuple[str, dict[str, Any]]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for raw in registry.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((raw, row))
    if not matches:
        raise ValueError(f"registry has no {HYPOTHESIS_ID} row")
    raw, row = matches[-1]
    if row.get("state") != "screened" or row.get("model") != 0:
        raise ValueError("latest HYP-003 registry row is not screened Model 0")
    return raw, row


def build(root: Path, output: Path) -> dict[str, Any]:
    package = root / "03. EA Developer" / EA_NAME
    source = package / f"{EA_NAME}.mq5"
    prereg = package / "research" / "HYP-VRAS-USDJPY-M5-003_FROZEN_PREREG.md"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    cost_manifest = output.parent / "cost_source_manifest.json"
    for required in (source, prereg, ea_contract, registry, cost_manifest):
        if not required.is_file():
            raise ValueError(f"required packet input is missing: {required}")
    raw_row, row = latest_registry_row(registry)
    source_hash = sha256_file(source)
    prereg_hash = sha256_file(prereg)
    if row.get("source_hash") != source_hash or row.get("prereg_sha256") != prereg_hash:
        raise ValueError("registry source/prereg binding does not match disk")

    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        output.write_text("{}\n", encoding="utf-8")
    commit = git_output(root, "rev-parse", "HEAD")[0].strip()
    status = git_output(root, "status", "--short", "--untracked-files=all")
    packet = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "source_path": repo_path(source, root),
        "source_sha256": source_hash,
        "registry_path": repo_path(registry, root),
        "registry_sha256": sha256_file(registry),
        "registry_row_sha256": sha256_bytes(raw_row.encode("utf-8")),
        "prereg_path": repo_path(prereg, root),
        "prereg_sha256": prereg_hash,
        "ea_contract_path": repo_path(ea_contract, root),
        "ea_contract_sha256": sha256_file(ea_contract),
        "telemetry_profile": "lifecycle-v3",
        "comparison_adapter": "generic-control-improvement-v1",
        "symbol": "USDJPY",
        "period": "M5",
        "from": "2016.01.04",
        "to": "2020.12.31",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": OVERRIDES,
        "telemetry_tier": "trade-only",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "validation_stage": "challenger",
        "holding_contract": "scalp",
        "cost_evidence_tier": "research_proxy",
        "acceptance_contract": ACCEPTANCE,
        "git_commit": commit,
        "git_status": status,
        "git_status_sha256": sha256_bytes("\n".join(status).encode("utf-8")),
        "include_closure": [],
        "include_closure_sha256": sha256_bytes(b""),
        "broker_fingerprint": "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54",
        "server_fingerprint": "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0",
        "account_fingerprint": "0635F9333630C605B51F8208861007B4267011E5F4D7C3C841309F04FE39BF02",
        "data_fingerprint": "FFD3024F94509DCC5281F6956A237BED542F9161F44837BF2AAE904D76D9B695",
        "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "required_sidecars": ["*_LifecycleTrades_*.csv", "*_RunMeta_*.json"],
        "required_manifest_hashes": [
            "source_sha256",
            "config_sha256",
            "report_sha256",
            "ex5_sha256",
            "includes_sha256",
        ],
        "cost_source_manifest_path": repo_path(cost_manifest, root),
        "cost_source_manifest_sha256": sha256_file(cost_manifest),
        "matched_control_run_id": "",
        "matched_control_hypothesis_id": "",
        "matched_control_manifest_sha256": "",
        "matched_control_report_sha256": "",
        "matched_control_overrides": "",
        "matched_control_source_sha256": "",
        "matched_control_config_sha256": "",
        "matched_control_ex5_sha256": "",
        "matched_control_includes_sha256": "",
        "matched_control_git_commit": "",
        "matched_control_git_status_sha256": "",
        "wfa_artifact_path": "",
        "wfa_artifact_sha256": "",
        "variants_dir": "",
        "variants_sha256": "",
    }
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=(
            "03. EA Developer/EA_VRAS_RegimeAdaptiveScalperV4/research/preflight/"
            "HYP-VRAS-USDJPY-M5-003/task_packet.control.json"
        ),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = (root / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out).resolve()
    packet = build(root, output)
    output.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(output), "git_status_sha256": packet["git_status_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
