#!/usr/bin/env python3
"""Build HYP-H1-THREEBAR-REV-001 sonic_execution_receipt.v1 + registry row."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer" / "EA_H1ThreeBarRev" / "EA_H1ThreeBarRev.mq5"
PREREG = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260714_H_H1_THREEBAR_REV_001_PREREG.md"
)
STUB = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "h1_threebar_rev"
    / "contracts"
    / "receipt_stubs_HYP_T3REV_001"
)
CONTRACTS = STUB.parent
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HID = "HYP-H1-THREEBAR-REV-001"
EA_NAME = "EA_H1ThreeBarRev"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def nogit_snapshot(active_source: Path) -> tuple[str, str]:
    agents = ROOT / "AGENTS.md"
    goal = ROOT / "01. GOAL" / "GOAL.md"
    paths = [agents, goal, active_source]
    records = []
    root_full = str(ROOT.resolve())
    for p in paths:
        full = str(p.resolve())
        if full.lower().startswith(root_full.lower()):
            rel = full[len(root_full) :].lstrip("\\/").replace("\\", "/")
        else:
            rel = full.replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(p)}")
    prov = sha256_text("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = ["nogit=true", "dirty=true", f"provenance_sha256={prov}"]
    return commit, sha256_text("\n".join(status))


def file_ev(label: str, path: Path) -> dict:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def main() -> None:
    STUB.mkdir(parents=True, exist_ok=True)
    git_commit, git_status_sha256 = nogit_snapshot(EA)

    task_packet = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": HID,
        "ea_name": EA_NAME,
        "symbol": "USDJPY",
        "period": "H1",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": "control",
        "note": "Post-PIN independent 3-bar rev RR=3 Model 0",
    }
    (STUB / "task_packet.json").write_text(json.dumps(task_packet, indent=2) + "\n", encoding="utf-8")
    (STUB / "prereg.json").write_text(
        json.dumps(
            {
                "hypothesis_id": HID,
                "prereg_md": str(PREREG),
                "prereg_sha256": sha256_file(PREREG),
                "frozen": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (STUB / "cost_source_manifest.json").write_text(
        json.dumps(
            {
                "hypothesis_id": HID,
                "cost_provenance": "UNVERIFIED",
                "spread_policy": "tester_current",
                "commission": "unknown_not_zero",
                "slippage": "unknown_not_zero",
                "note": "Model 0 screen; missing cost != 0.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (STUB / "include_note.txt").write_text(
        "EA_H1ThreeBarRev is single-file; Trade.mqh is MT5 standard library. "
        "Stub satisfies include_* receipt closure for Model 0 screen.\n",
        encoding="utf-8",
    )

    evidence = [
        file_ev("task_packet", STUB / "task_packet.json"),
        file_ev("source", EA),
        file_ev("prereg", STUB / "prereg.json"),
        file_ev("cost_source_manifest", STUB / "cost_source_manifest.json"),
        file_ev("include_0001", STUB / "include_note.txt"),
    ]
    include_items = [e for e in evidence if e["label"].startswith("include_")]
    include_records = []
    for e in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
        path = str(Path(e["path"]).resolve()).lower()
        include_records.append(f"{path}\t{e['sha256'].upper()}")
    include_closure = sha256_text("\n".join(include_records))

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HID,
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha256,
        "binding": {
            "hypothesis_id": HID,
            "run_role": "control",
            "ea_name": EA_NAME,
            "symbol": "USDJPY",
            "period": "H1",
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
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Independent H1 three-bar reversal RR=3 after PIN kill",
    }
    receipt_path = CONTRACTS / "20260714_HYP_H1_THREEBAR_REV_001_CONTRACT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (CONTRACTS / "20260714_HYP_H1_THREEBAR_REV_001_CONTRACT_RECEIPT.json.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )

    row = {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": HID,
        "state": "preregistered",
        "parent_candidate": "HYP-H1-PIN-PDLEVEL-001",
        "feature_family": "h1_three_bar_reversal",
        "lane": "post_pin_thick_edge_20260714",
        "setup_type": "H1 classic 3-bar rev; MinBodyFrac 0.35; RR=3; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "H1",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Post PIN KILL independent structure; GPT waived",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_THREEBAR_REV_001_PREREG.md",
        "readout_path": None,
        "exact_overrides": "",
        "variant_tag": "HYP_H1_THREEBAR_REV_001_MODEL0",
        "source_path": "03. EA Developer/EA_H1ThreeBarRev/EA_H1ThreeBarRev.mq5",
        "source_hash": sha256_file(EA),
        "run_ids": [],
        "metrics": None,
        "validation": {
            "cost_stress": "tester current + a priori +$12 if PF>=1.20",
            "dedup": "readouts/20260714_H1_THREEBAR_REV_DEDUP_CLEARANCE.md",
        },
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "verdict": "PREREG_FROZEN",
        "contract_receipt_sha256": receipt_sha,
        "updated_at": "2026-07-14",
    }
    with REG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "hypothesis_id": HID,
        "ea_name": EA_NAME,
        "period": "H1",
        "deposit": 100000,
        "receipt": str(receipt_path),
        "receipt_sha256": receipt_sha,
        "source_sha256": sha256_file(EA),
        "git_commit": git_commit,
    }
    meta_path = (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / "20260714_H1_THREEBAR_REV_CONTRACT_META.json"
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
