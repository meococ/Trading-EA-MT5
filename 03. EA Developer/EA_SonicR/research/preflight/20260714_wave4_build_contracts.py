#!/usr/bin/env python3
"""Build Wave4 ContractReceipts for IB / RVCompress / GBPJPYLead."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")

SPECS = [
    {
        "hyp": "HYP-M15-IB-OVERLAP-BREAK-001",
        "ea_name": "EA_M15IBOverlapBreak",
        "ea": ROOT / "03. EA Developer" / "EA_M15IBOverlapBreak" / "EA_M15IBOverlapBreak.mq5",
        "prereg": ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preregs"
        / "20260714_H_M15_IB_OVERLAP_BREAK_001_PREREG.md",
        "folder": "m15_ib_overlap_break",
        "stub": "receipt_stubs_HYP_IBOV_001",
        "receipt_name": "20260714_HYP_M15_IB_OVERLAP_BREAK_001_CONTRACT_RECEIPT.json",
        "period": "M15",
        "deposit": 100000,
        "note": "Wave4 Model 0; London IB → overlap break RR=2.5",
    },
    {
        "hyp": "HYP-H1-RV-COMPRESS-BREAK-001",
        "ea_name": "EA_H1RVCompressBreak",
        "ea": ROOT / "03. EA Developer" / "EA_H1RVCompressBreak" / "EA_H1RVCompressBreak.mq5",
        "prereg": ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preregs"
        / "20260714_H_H1_RV_COMPRESS_BREAK_001_PREREG.md",
        "folder": "h1_rv_compress_break",
        "stub": "receipt_stubs_HYP_RVCB_001",
        "receipt_name": "20260714_HYP_H1_RV_COMPRESS_BREAK_001_CONTRACT_RECEIPT.json",
        "period": "H1",
        "deposit": 100000,
        "note": "Wave4 Model 0; H1 RV-compress Donchian break RR=2.5",
    },
    {
        "hyp": "HYP-GBPJPY-LEAD-USDJPY-H1-001",
        "ea_name": "EA_H1GBPJPYLead",
        "ea": ROOT / "03. EA Developer" / "EA_H1GBPJPYLead" / "EA_H1GBPJPYLead.mq5",
        "prereg": ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preregs"
        / "20260714_H_GBPJPY_LEAD_USDJPY_H1_001_PREREG.md",
        "folder": "h1_gbpjpy_lead",
        "stub": "receipt_stubs_HYP_GBPJPY_001",
        "receipt_name": "20260714_HYP_GBPJPY_LEAD_USDJPY_H1_001_CONTRACT_RECEIPT.json",
        "period": "H1",
        "deposit": 100000,
        "note": "Wave4 Model 0; GBPJPY ATR impulse lead → USDJPY lag RR=2.5",
    },
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def nogit_snapshot(ea: Path) -> tuple[str, str]:
    paths = [ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", ea]
    records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
    prov = sha256_text("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    return commit, sha256_text(status)


def build_one(spec: dict) -> dict:
    contracts = (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / spec["folder"]
        / "contracts"
    )
    stubs = contracts / spec["stub"]
    contracts.mkdir(parents=True, exist_ok=True)
    stubs.mkdir(parents=True, exist_ok=True)

    ea = spec["ea"]
    prereg_md = spec["prereg"]
    hyp = spec["hyp"]
    ea_name = spec["ea_name"]
    period = spec["period"]
    deposit = spec["deposit"]

    task_obj = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": hyp,
        "ea_name": ea_name,
        "symbol": "USDJPY",
        "period": period,
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": "control",
        "note": spec["note"],
    }
    prereg_obj = {
        "schema_version": "sonic_prereg.v1",
        "hypothesis_id": hyp,
        "status": "FROZEN",
        "prereg_md": str(prereg_md.resolve()),
        "prereg_md_sha256": sha256_file(prereg_md),
    }
    cost_obj = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "hypothesis_id": hyp,
        "status": "UNVERIFIED_TESTER_DEFAULT",
        "policy": "DOCUMENTED_RESEARCH_PROXY",
        "spread": "current",
        "note": (
            "Wave4 Model 0 under tester-current; a priori +$12 stress if PF>=1.20. "
            "Not Real QFSI / not GOAL."
        ),
        "promotion_eligible": False,
    }

    task = stubs / "task_packet.json"
    prereg = stubs / "prereg.json"
    cost = stubs / "cost_source_manifest.json"
    include = stubs / "include_note.txt"
    task.write_text(json.dumps(task_obj, indent=2) + "\n", encoding="utf-8")
    prereg.write_text(json.dumps(prereg_obj, indent=2) + "\n", encoding="utf-8")
    cost.write_text(json.dumps(cost_obj, indent=2) + "\n", encoding="utf-8")
    include.write_text(
        f"{ea_name} is single-file; Trade.mqh is MT5 standard library. "
        "Stub satisfies include_* receipt closure for Model 0 screen.\n",
        encoding="utf-8",
    )

    h_task = sha256_file(task)
    h_prereg = sha256_file(prereg)
    h_cost = sha256_file(cost)
    h_include = sha256_file(include)
    h_source = sha256_file(ea)
    include_closure = sha256_text(f"{str(include.resolve()).lower()}\t{h_include}")
    git_commit, git_status_sha = nogit_snapshot(ea)

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": hyp,
        "task_packet_sha256": h_task,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": hyp,
            "run_role": "control",
            "ea_name": ea_name,
            "symbol": "USDJPY",
            "period": period,
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": "",
            "telemetry_tier": "off",
            "deposit": deposit,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": [
            {"label": "task_packet", "kind": "file", "path": str(task.resolve()), "sha256": h_task},
            {"label": "source", "kind": "file", "path": str(ea.resolve()), "sha256": h_source},
            {"label": "prereg", "kind": "file", "path": str(prereg.resolve()), "sha256": h_prereg},
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
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": spec["note"],
    }

    receipt_path = contracts / spec["receipt_name"]
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (contracts / (spec["receipt_name"] + ".sha256.txt")).write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(f"{hyp}|{receipt_path}|{receipt_sha}")
    return {
        "hypothesis_id": hyp,
        "ea_name": ea_name,
        "period": period,
        "deposit": deposit,
        "receipt": str(receipt_path),
        "receipt_sha256": receipt_sha,
    }


def main() -> None:
    out = [build_one(s) for s in SPECS]
    manifest = (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / "20260714_DISCOVERY_WAVE4_CONTRACTS.json"
    )
    manifest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("MANIFEST", manifest)


if __name__ == "__main__":
    main()
