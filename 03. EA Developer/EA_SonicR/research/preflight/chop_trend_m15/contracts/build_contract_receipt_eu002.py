#!/usr/bin/env python3
"""Build ContractReceipt for HYP-CHOP-TREND-EU-M15-002 (Europe hours override)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
CONTRACTS = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "chop_trend_m15"
    / "contracts"
)
STUBS = CONTRACTS / "receipt_stubs_HYP_CHOP_TREND_EU_M15_002"
EA = ROOT / "03. EA Developer" / "EA_M15ChopTrend" / "EA_M15ChopTrend.mq5"
PREREG_MD = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260714_H_CHOP_TREND_EU_M15_002_PREREG.md"
)
RECEIPT = CONTRACTS / "20260714_HYP_CHOP_TREND_EU_M15_002_CONTRACT_RECEIPT.json"

HYP = "HYP-CHOP-TREND-EU-M15-002"
EA_NAME = "EA_M15ChopTrend"
FROM = "2021.01.01"
TO = "2025.12.31"
SYMBOL = "USDJPY"
PERIOD = "M15"
OVERRIDES = "InpStartHour=10;InpEndHour=14"
MODEL = 0
DEPOSIT = 10000
LEVERAGE = 100


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def nogit_snapshot() -> tuple[str, str]:
    paths = [
        ROOT / "AGENTS.md",
        ROOT / "01. GOAL" / "GOAL.md",
        EA,
    ]
    records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
    prov = sha256_text("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    return commit, sha256_text(status)


def main() -> int:
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    STUBS.mkdir(parents=True, exist_ok=True)

    stubs = {
        "task_packet.json": {
            "schema_version": "sonic_research_task_packet.v1",
            "hypothesis_id": HYP,
            "ea_name": EA_NAME,
            "symbol": SYMBOL,
            "period": PERIOD,
            "from": FROM,
            "to": TO,
            "model": MODEL,
            "run_role": "control",
            "overrides": OVERRIDES,
            "note": "Europe-hour child of ChopTrend 001 near_miss; cost not broker-verified.",
        },
        "prereg.json": {
            "schema_version": "sonic_prereg.v1",
            "hypothesis_id": HYP,
            "status": "FROZEN",
            "prereg_md": str(PREREG_MD.resolve()),
            "prereg_md_sha256": sha256_file(PREREG_MD),
        },
        "cost_source_manifest.json": {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "hypothesis_id": HYP,
            "status": "UNVERIFIED_TESTER_DEFAULT",
            "note": "Missing/zero cost fields must NOT be treated as zero friction.",
        },
    }
    for name, obj in stubs.items():
        (STUBS / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    include = STUBS / "include_note.txt"
    include.write_text(
        "EA_M15ChopTrend is single-file; Trade.mqh is MT5 standard library. "
        "This stub satisfies include_* receipt closure for Model 0 screen.\n",
        encoding="utf-8",
    )

    task = STUBS / "task_packet.json"
    prereg = STUBS / "prereg.json"
    cost = STUBS / "cost_source_manifest.json"

    h_task, h_prereg, h_cost, h_include, h_source = (
        sha256_file(task),
        sha256_file(prereg),
        sha256_file(cost),
        sha256_file(include),
        sha256_file(EA),
    )
    include_closure = sha256_text(f"{str(include.resolve()).lower()}\t{h_include}")
    git_commit, git_status_sha = nogit_snapshot()

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HYP,
        "task_packet_sha256": h_task,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": HYP,
            "run_role": "control",
            "ea_name": EA_NAME,
            "symbol": SYMBOL,
            "period": PERIOD,
            "from": FROM,
            "to": TO,
            "model": MODEL,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": OVERRIDES,
            "telemetry_tier": "off",
            "deposit": DEPOSIT,
            "leverage": LEVERAGE,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": [
            {"label": "task_packet", "kind": "file", "path": str(task.resolve()), "sha256": h_task},
            {"label": "source", "kind": "file", "path": str(EA.resolve()), "sha256": h_source},
            {"label": "prereg", "kind": "file", "path": str(prereg.resolve()), "sha256": h_prereg},
            {"label": "cost_source_manifest", "kind": "file", "path": str(cost.resolve()), "sha256": h_cost},
            {"label": "include_0001", "kind": "file", "path": str(include.resolve()), "sha256": h_include},
        ],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Model 0 Europe-hour child. Binding must match alpha.ps1. Cost unverified.",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(RECEIPT)
    (CONTRACTS / "20260714_HYP_CHOP_TREND_EU_M15_002_CONTRACT_RECEIPT.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(f"RECEIPT_SHA256={receipt_sha}")
    print(f"RECEIPT_PATH={RECEIPT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
