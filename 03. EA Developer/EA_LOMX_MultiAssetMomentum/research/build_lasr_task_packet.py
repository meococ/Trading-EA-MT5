#!/usr/bin/env python3
"""Build the frozen HYP-LASR-XAUUSD-M5-001 task packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-LASR-XAUUSD-M5-001"
EA_NAME = "EA_LOMX_MultiAssetMomentum"
OVERRIDES = (
    "InpResearchAutoMode=true;InpEnableTelemetry=true;"
    "InpHypothesisId=HYP-LASR-XAUUSD-M5-001;"
    "InpVariantTag=LASR_XAU_SWEEP_MODEL0;InpEngineMode=0;"
    "InpMagic=5603101;InpRiskPercent=0.25;InpMaxDailyLossPct=3.5;"
    "InpMaxAccountDrawdownPct=8.0;InpMaxTradesPerDay=3;"
    "InpMaxSpreadToRisk=0.15;InpDeviationPoints=20;InpATRPeriod=14;"
    "InpSweepEpsilonMult=0.30;InpSweepStopAtrMult=0.20;"
    "InpSweepMinTp2R=1.50;InpVolumeLookback=20;InpVolumeThreshold=1.50;"
    "InpAsianStartMinutesUtc=0;InpAsianEndMinutesUtc=360;"
    "InpTradeStartMinutesUtc=420;InpTradeEndMinutesUtc=960;"
    "InpDailyFlattenMinutesUtc=1200;InpFridayFlattenMinutesUtc=1200;"
    "InpSweepScaleOutFraction=0.50;InpMaxHoldBars=96;"
    "InpLotConsistencyMinFills=10;InpLotConsistencyLookbackFills=10;"
    "InpLotConsistencyMinFactor=0.50;InpLotConsistencyMaxFactor=1.50"
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
        raise ValueError("latest HYP-LASR registry row is not screened Model 0")
    return raw, row


def build(root: Path, output: Path) -> dict[str, Any]:
    package = root / "03. EA Developer" / EA_NAME
    source = package / f"{EA_NAME}.mq5"
    prereg = package / "research" / "HYP-LASR-XAUUSD-M5-001_FROZEN_PREREG.md"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    cost_manifest = package / "research" / "preflight" / HYPOTHESIS_ID / "cost_source_manifest.json"
    for required in (source, prereg, ea_contract, registry, cost_manifest):
        if not required.is_file():
            raise ValueError(f"required packet input is missing: {required}")

    raw_row, row = latest_registry_row(registry)
    source_hash = sha256_file(source)
    prereg_hash = sha256_file(prereg)
    if row.get("source_hash") != source_hash or row.get("prereg_sha256") != prereg_hash:
        raise ValueError("registry source/prereg binding does not match disk")

    cost = json.loads(cost_manifest.read_text(encoding="utf-8-sig"))
    output.parent.mkdir(parents=True, exist_ok=True)
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
        "symbol": "XAUUSD",
        "period": "M5",
        "from": "2018.01.02",
        "to": "2022.12.30",
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
        "broker_fingerprint": cost["broker_fingerprint"],
        "server_fingerprint": cost["server_fingerprint"],
        "account_fingerprint": cost["account_fingerprint"],
        "data_fingerprint": cost["data_fingerprint"],
        "symbol_geometry": cost["symbol_geometry"],
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
            "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/preflight/"
            "HYP-LASR-XAUUSD-M5-001/task_packet.control.json"
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
