#!/usr/bin/env python3
"""Build the guarded HYP-LASR-EURUSD-M5-002 Model-0 task packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-LASR-EURUSD-M5-002"
EA_NAME = "EA_LOMX_MultiAssetMomentum"
OVERRIDES = (
    "InpAsianEndMinutesUtc=360;InpAsianStartMinutesUtc=0;InpATRPeriod=14;"
    "InpDailyFlattenMinutesUtc=1200;InpDeviationPoints=20;"
    "InpEnableTelemetry=true;InpEngineMode=0;InpFridayFlattenMinutesUtc=1200;"
    "InpHypothesisId=HYP-LASR-EURUSD-M5-002;"
    "InpLotConsistencyLookbackFills=10;InpLotConsistencyMaxFactor=1.50;"
    "InpLotConsistencyMinFactor=0.50;InpLotConsistencyMinFills=10;"
    "InpMagic=5603103;InpMaxAccountDrawdownPct=8.0;"
    "InpMaxDailyLossPct=3.5;InpMaxHoldBars=96;InpMaxSpreadToRisk=0.15;"
    "InpMaxTradesPerDay=3;InpResearchAutoMode=true;InpRiskPercent=0.25;"
    "InpSweepEpsilonMult=0.30;InpSweepMinTp2R=1.50;"
    "InpSweepScaleOutFraction=0.50;InpSweepStopAtrMult=0.20;"
    "InpTradeEndMinutesUtc=960;InpTradeStartMinutesUtc=420;"
    "InpVariantTag=LASR_EUR_SWEEP_MARGINSAFE_MODEL0;InpVolumeLookback=20;"
    "InpVolumeThreshold=1.50"
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


def normalized_overrides(text: str) -> dict[str, str]:
    values = dict(item.split("=", 1) for item in text.split(";") if item)
    if values.get("InpEngineMode") == "ENGINE_SWEEP":
        values["InpEngineMode"] = "0"
    return dict(sorted(values.items()))


def git_output(root: Path, *args: str) -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.decode("utf-8").splitlines()


def assert_registry_valid(root: Path, registry: Path) -> None:
    validator = root / "04. Memory" / "research" / "validate_candidate_registry.py"
    completed = subprocess.run(
        ["python", str(validator), "--registry", str(registry)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = completed.stdout.decode("utf-8", errors="replace")
    if completed.returncode != 0 or "CANDIDATE_REGISTRY_OK" not in output:
        raise ValueError(f"candidate registry is not canonically valid:\n{output}")


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
        raise ValueError("latest EURUSD successor row is not screened Model 0")
    validation = row.get("validation") or {}
    if validation.get("model0_authorized") is not True:
        raise ValueError("latest EURUSD successor row does not authorize Model 0")
    return raw, row


def frozen_prereg_overrides(prereg: Path) -> str:
    match = re.search(
        r"Exact overrides, sorted and immutable:\s*```text\s*(.+?)\s*```",
        prereg.read_text(encoding="utf-8"),
        re.S,
    )
    if match is None:
        raise ValueError("prereg exact override block is missing")
    return match.group(1).strip()


def build(root: Path, output: Path) -> dict[str, Any]:
    package = root / "03. EA Developer" / EA_NAME
    source = package / f"{EA_NAME}.mq5"
    prereg = package / "research" / f"{HYPOTHESIS_ID}_FROZEN_PREREG.md"
    ea_contract = package / "ALPHAFACTORY_EA_CONTRACT.json"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    cost_manifest = package / "research" / "preflight" / HYPOTHESIS_ID / "cost_source_manifest.json"
    for required in (source, prereg, ea_contract, registry, cost_manifest):
        if not required.is_file():
            raise ValueError(f"required packet input is missing: {required}")

    assert_registry_valid(root, registry)
    raw_row, row = latest_registry_row(registry)
    source_hash = sha256_file(source)
    prereg_hash = sha256_file(prereg)
    if row.get("source_hash") != source_hash or row.get("prereg_sha256") != prereg_hash:
        raise ValueError("registry source/prereg binding does not match disk")
    frozen = normalized_overrides(frozen_prereg_overrides(prereg))
    if normalized_overrides(OVERRIDES) != frozen:
        raise ValueError("builder overrides do not match frozen prereg")
    if normalized_overrides(str(row.get("exact_overrides") or "")) != frozen:
        raise ValueError("registry overrides do not match frozen prereg")

    cost = json.loads(cost_manifest.read_text(encoding="utf-8-sig"))
    if cost.get("evidence_tier") != "RESEARCH_PROXY" or cost.get("promotion_eligible") is not False:
        raise ValueError("cost manifest must be a non-promotable research proxy")

    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists():
        output.write_text("{}\n", encoding="utf-8")
    commit = git_output(root, "rev-parse", "HEAD")[0].strip()
    status = git_output(root, "status", "--short", "--untracked-files=all")
    return {
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
        "symbol": "EURUSD",
        "period": "M5",
        "from": "2016.01.04",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=(
            "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/preflight/"
            "HYP-LASR-EURUSD-M5-002/task_packet.control.json"
        ),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    requested = Path(args.out)
    output = requested.resolve() if requested.is_absolute() else (root / requested).resolve()
    packet = build(root, output)
    output.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(output),
                "registry_sha256": packet["registry_sha256"],
                "git_status_sha256": packet["git_status_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
