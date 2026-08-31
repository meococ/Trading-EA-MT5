#!/usr/bin/env python3
"""Build control contract receipt for HYP-HIS-DIAG-GATECOUNT-M15-EUR-001 (Owner B)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HYP = "HYP-HIS-DIAG-GATECOUNT-M15-EUR-001"
EA_NAME = "EA_HybridICT_Sonic"
SYMBOL = "EURUSD"
PERIOD = "M15"
FROM = "2020.01.01"
TO = "2026.07.15"
DEPOSIT = 100000
LEVERAGE = 100
MODEL = 0
RUN_ROLE = "control"
# Sorted A-Z for alpha.ps1 NormalizeOverrideMap
OVERRIDES = (
    "InpDiagGateLog=true;InpLevelTouchATR=0.50;InpMaxAtrRatio=3.00;"
    "InpMaxSpreadPips=4.0;InpMinAtrRatio=0.70;InpRequireMacdSlope=false;"
    "InpRequirePvsraClimax=true;InpRequireWave=true;InpUseDragonSlFloor=false;"
    "InpVolClimaxMult=1.5"
)
TELEMETRY = "off"
SPREAD = "current"

EA = ROOT / "03. EA Developer/EA_HybridICT_Sonic/EA_HybridICT_Sonic.mq5"
HELPER = ROOT / "03. EA Developer/EA_HybridICT_Sonic/Include/HIS_Helpers.mqh"
PREREG = ROOT / (
    "03. EA Developer/EA_HybridICT_Sonic/research/"
    "20260715_HYP_HIS_DIAG_GATECOUNT_M15_EUR_001_PREREG.md"
)
STUB = ROOT / (
    "03. EA Developer/EA_HybridICT_Sonic/research/preflight/"
    "hybrid_ict_sonic/contracts/receipt_stubs_HYP_HIS_DIAG_GATECOUNT_M15_EUR_001"
)
CONTRACTS = STUB.parent
RECEIPT_NAME = "20260715_HYP_HIS_DIAG_GATECOUNT_M15_EUR_001_CONTRACT_RECEIPT.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def git_snapshot() -> tuple[str, str]:
    commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=all"],
        text=True,
    )
    return commit, sha256_text("\n".join(status.splitlines()))


def file_ev(label: str, path: Path) -> dict:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def main() -> None:
    STUB.mkdir(parents=True, exist_ok=True)
    task_packet = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": HYP,
        "ea_name": EA_NAME,
        "symbol": SYMBOL,
        "period": PERIOD,
        "from": FROM,
        "to": TO,
        "model": MODEL,
        "run_role": RUN_ROLE,
        "overrides": OVERRIDES,
        "deposit": DEPOSIT,
        "leverage": LEVERAGE,
        "note": "Owner B DIAG: DragonSlFloor=false + gate counters. Not promotion.",
    }
    (STUB / "task_packet.json").write_text(
        json.dumps(task_packet, indent=2) + "\n", encoding="utf-8"
    )
    (STUB / "prereg.json").write_text(
        json.dumps(
            {
                "hypothesis_id": HYP,
                "prereg_path": str(PREREG),
                "prereg_sha256": sha256_file(PREREG),
                "frozen": True,
                "parent_hyp": "HYP-HYBRID-ICT-SONIC-M15-EURGBP-001",
                "offline_gatecount_sha256": "FDCB7258A7385C97833D619209C03C25E40D8B12FE0DCF58F455857E6523D006",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (STUB / "cost_source_manifest.json").write_text(
        json.dumps(
            {
                "cost_provenance": "UNVERIFIED",
                "spread_policy": "tester_current",
                "commission": "unknown_not_zero",
                "slippage": "unknown_not_zero",
                "note": "DIAG screen only; missing cost != 0.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    evidence = [
        file_ev("task_packet", STUB / "task_packet.json"),
        file_ev("source", EA),
        file_ev("prereg", STUB / "prereg.json"),
        file_ev("cost_source_manifest", STUB / "cost_source_manifest.json"),
        file_ev("include_0001", HELPER),
    ]
    include_items = [e for e in evidence if e["label"].startswith("include_")]
    include_records = []
    for item in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
        path = str(Path(item["path"]).resolve()).lower()
        include_records.append(f"{path}\t{item['sha256'].upper()}")
    include_closure = sha256_text("\n".join(include_records))

    receipt_path = CONTRACTS / RECEIPT_NAME
    sha_path = CONTRACTS / (RECEIPT_NAME + ".sha256.txt")
    receipt_path.write_text("{}\n", encoding="utf-8")
    sha_path.write_text("PENDING\n", encoding="utf-8")
    commit, status_sha = git_snapshot()

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HYP,
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": HYP,
            "run_role": RUN_ROLE,
            "ea_name": EA_NAME,
            "symbol": SYMBOL,
            "period": PERIOD,
            "from": FROM,
            "to": TO,
            "model": MODEL,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": OVERRIDES,
            "telemetry_tier": TELEMETRY,
            "deposit": DEPOSIT,
            "leverage": LEVERAGE,
            "spread": SPREAD,
            "required_sidecars": [],
            "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Owner B DIAG control. Binding must match alpha.ps1. Not promotion.",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    sha_path.write_text(receipt_sha + "\n", encoding="utf-8")
    commit2, status_sha2 = git_snapshot()
    if commit2 != commit or status_sha2 != status_sha:
        raise SystemExit("git status drifted while minting DIAG receipt")
    print("RECEIPT", receipt_path)
    print("RECEIPT_SHA256", receipt_sha)


if __name__ == "__main__":
    main()
