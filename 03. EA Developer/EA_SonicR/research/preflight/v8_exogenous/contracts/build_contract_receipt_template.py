#!/usr/bin/env python3
"""Build ContractReceipt template for HYP_CARRY_PUBLIC_RATES_D1_001 and print SHA256."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
CONTRACTS = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "v8_exogenous"
    / "contracts"
)
STUBS = CONTRACTS / "receipt_stubs_HYP_CARRY_PUBLIC_RATES_D1_001"
EA = ROOT / "03. EA Developer" / "EA_CarryPublicRates" / "EA_CarryPublicRates.mq5"
RECEIPT = CONTRACTS / "20260713_HYP_CARRY_PUBLIC_RATES_D1_001_CONTRACT_RECEIPT.json"


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
    records = []
    for p in paths:
        records.append(f"{rel(p)}\t{sha256_file(p)}")
    payload = "\n".join(records)
    prov = sha256_text(payload)
    commit = f"NOGIT-{prov}"
    status = "\n".join(
        ["nogit=true", "dirty=true", f"provenance_sha256={prov}"]
    )
    return commit, sha256_text(status)


def main() -> int:
    STUBS.mkdir(parents=True, exist_ok=True)
    stubs = {
        "task_packet.json": {
            "schema_version": "sonic_research_task_packet.v1",
            "hypothesis_id": "HYP_CARRY_PUBLIC_RATES_D1_001",
            "note": "TEMPLATE stub for ContractReceipt scaffolding. Refresh hashes before live Model 0.",
        },
        "prereg.json": {
            "schema_version": "sonic_prereg.v1",
            "hypothesis_id": "HYP_CARRY_PUBLIC_RATES_D1_001",
            "status": "TEMPLATE_STUB",
            "note": "Not a frozen prereg. Replace before Model 0.",
        },
        "cost_source_manifest.json": {
            "schema_version": "alphafactory_cost_source_manifest.v1",
            "hypothesis_id": "HYP_CARRY_PUBLIC_RATES_D1_001",
            "status": "TEMPLATE_STUB",
            "note": "Cost fields must not be treated as zero. Replace with verified cost artifact before Model 0.",
        },
    }
    for name, obj in stubs.items():
        (STUBS / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    include = STUBS / "include_note.txt"
    include.write_text(
        "EA_CarryPublicRates is single-file; Trade.mqh is MT5 standard library. "
        "This stub satisfies include_* receipt closure for template validation only.\n",
        encoding="utf-8",
    )

    task = STUBS / "task_packet.json"
    prereg = STUBS / "prereg.json"
    cost = STUBS / "cost_source_manifest.json"

    h_task = sha256_file(task)
    h_prereg = sha256_file(prereg)
    h_cost = sha256_file(cost)
    h_include = sha256_file(include)
    h_source = sha256_file(EA)

    include_record = f"{str(include.resolve()).lower()}\t{h_include}"
    include_closure = sha256_text(include_record)
    git_commit, git_status_sha = nogit_snapshot()

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": "HYP_CARRY_PUBLIC_RATES_D1_001",
        "task_packet_sha256": h_task,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": "HYP_CARRY_PUBLIC_RATES_D1_001",
            "run_role": "control",
            "ea_name": "EA_CarryPublicRates",
            "symbol": "EURUSD",
            "period": "D1",
            "from": "2019.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": "",
            "telemetry_tier": "off",
            "deposit": 10000,
            "leverage": 100,
            "spread": "",
            "required_sidecars": [],
            "symbol_geometry": {
                "digits": 5,
                "point": 0.00001,
                "pip_size": 0.0001,
            },
            "include_closure_sha256": include_closure,
        },
        "evidence": [
            {
                "label": "task_packet",
                "kind": "file",
                "path": str(task.resolve()),
                "sha256": h_task,
            },
            {
                "label": "source",
                "kind": "file",
                "path": str(EA.resolve()),
                "sha256": h_source,
            },
            {
                "label": "prereg",
                "kind": "file",
                "path": str(prereg.resolve()),
                "sha256": h_prereg,
            },
            {
                "label": "cost_source_manifest",
                "kind": "file",
                "path": str(cost.resolve()),
                "sha256": h_cost,
            },
            {
                "label": "include_0001",
                "kind": "file",
                "path": str(include.resolve()),
                "sha256": h_include,
            },
        ],
        "generated_at_utc": "2026-07-13T16:40:00Z",
        "note": (
            "TEMPLATE: binding must match alpha backtest invocation exactly; "
            "refresh SHA256 after any evidence edit. HypothesisId + ContractReceipt "
            "requirements remain mandatory. git_commit uses NO-GIT provenance."
        ),
    }

    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(RECEIPT)
    print(f"GIT_COMMIT={git_commit}")
    print(f"GIT_STATUS_SHA256={git_status_sha}")
    print(f"RECEIPT_PATH={RECEIPT}")
    print(f"RECEIPT_SHA256={receipt_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
