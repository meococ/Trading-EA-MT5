#!/usr/bin/env python3
"""Build control ContractReceipt for Spark Deposit=100000 capital twin."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "sb_spark_book"
EA = ROOT / "03. EA Developer" / "EA_M15SparkAsian" / "EA_M15SparkAsian.mq5"
PREREG = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260714_H_SB_SPARK_BOOK_001_PREREG.md"
)
HYP = "HYP-SB-SPARK-BOOK-001"


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


def main() -> int:
    contracts = PRE / "contracts"
    stubs = contracts / "receipt_stubs_HYP_SB_SPARK_BOOK_001_SPARK_CAP100K"
    contracts.mkdir(parents=True, exist_ok=True)
    stubs.mkdir(parents=True, exist_ok=True)

    task = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": HYP,
        "ea_name": "EA_M15SparkAsian",
        "symbol": "USDJPY",
        "period": "M15",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": "control",
        "overrides": "",
        "deposit": 100000,
        "note": "Spark capital twin Deposit=100000 for honest SB+Spark book join.",
    }
    prereg = {
        "schema_version": "sonic_prereg.v1",
        "hypothesis_id": HYP,
        "status": "FROZEN_RESEARCH_SCREEN",
        "prereg_md": str(PREREG.resolve()),
        "prereg_md_sha256": sha256_file(PREREG),
        "overrides": "",
    }
    cost = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "hypothesis_id": HYP,
        "status": "UNVERIFIED_TESTER_DEFAULT",
        "policy": "DOCUMENTED_RESEARCH_PROXY",
        "spread": "current",
        "promotion_eligible": False,
    }
    for name, obj in {
        "task_packet.json": task,
        "prereg.json": prereg,
        "cost_source_manifest.json": cost,
    }.items():
        (stubs / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    include = stubs / "include_note.txt"
    include.write_text(
        "EA_M15SparkAsian capital twin control; closed-bar[1]; include closure stub.\n",
        encoding="utf-8",
    )

    tpath, ppath, cpath = stubs / "task_packet.json", stubs / "prereg.json", stubs / "cost_source_manifest.json"
    h_task, h_prereg, h_cost = sha256_file(tpath), sha256_file(ppath), sha256_file(cpath)
    h_include, h_source = sha256_file(include), sha256_file(EA)
    include_closure = sha256_text(f"{str(include.resolve()).lower()}\t{h_include}")
    git_commit, git_status_sha = nogit_snapshot(EA)

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HYP,
        "task_packet_sha256": h_task,
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha,
        "binding": {
            "hypothesis_id": HYP,
            "run_role": "control",
            "ea_name": "EA_M15SparkAsian",
            "symbol": "USDJPY",
            "period": "M15",
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": "",
            "telemetry_tier": "off",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": [
            {"label": "task_packet", "kind": "file", "path": str(tpath.resolve()), "sha256": h_task},
            {"label": "source", "kind": "file", "path": str(EA.resolve()), "sha256": h_source},
            {"label": "prereg", "kind": "file", "path": str(ppath.resolve()), "sha256": h_prereg},
            {"label": "cost_source_manifest", "kind": "file", "path": str(cpath.resolve()), "sha256": h_cost},
            {"label": "include_0001", "kind": "file", "path": str(include.resolve()), "sha256": h_include},
        ],
        "generated_at_utc": "2026-07-14T12:35:00Z",
        "note": "Capital twin control for SB+Spark book; Deposit 100000; no signal densify.",
    }
    receipt_path = contracts / "20260714_HYP_SB_SPARK_BOOK_001_SPARK_CAP100K_CONTRACT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (contracts / "20260714_HYP_SB_SPARK_BOOK_001_SPARK_CAP100K_CONTRACT_RECEIPT.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(receipt_sha)
    print(receipt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
