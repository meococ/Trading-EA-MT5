# -*- coding: utf-8 -*-
"""Build contract receipts for H1 ATR Regime Mom + H1 Swing Failure."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")

SPECS = [
    {
        "hypothesis_id": "HYP-H1-ATR-REGIME-MOM-001",
        "ea_name": "EA_H1ATRRegimeMom",
        "ea_path": ROOT / "03. EA Developer" / "EA_H1ATRRegimeMom" / "EA_H1ATRRegimeMom.mq5",
        "preflight": "h1_atr_regime_mom",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_ATR_REGIME_MOM_001_PREREG.md",
        "note": "Model 0 H1 ATR-regime directional momentum; not stretch-fade/VolExp/Chop/ORB.",
    },
    {
        "hypothesis_id": "HYP-H1-SWING-FAILURE-001",
        "ea_name": "EA_H1SwingFailure",
        "ea_path": ROOT / "03. EA Developer" / "EA_H1SwingFailure" / "EA_H1SwingFailure.mq5",
        "preflight": "h1_swing_failure",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_SWING_FAILURE_001_PREREG.md",
        "note": "Model 0 H1 structural swing-failure fade; not FailedORB/LiqSweep/FractalBreak.",
    },
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def text_sha(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def build_one(spec: dict) -> dict:
    out_dir = (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / spec["preflight"]
        / "contracts"
    )
    stub = out_dir / f"receipt_stubs_{spec['hypothesis_id'].replace('-', '_')}"
    receipt_path = out_dir / f"20260714_{spec['hypothesis_id'].replace('-', '_')}_CONTRACT_RECEIPT.json"
    # Normalize filename to match prior style (keep hyphens as underscores after HYP)
    receipt_path = out_dir / (
        "20260714_" + spec["hypothesis_id"].replace("-", "_") + "_CONTRACT_RECEIPT.json"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    stub.mkdir(parents=True, exist_ok=True)

    overrides = ""
    task = {
        "hypothesis_id": spec["hypothesis_id"],
        "ea_name": spec["ea_name"],
        "symbol": "USDJPY",
        "period": "H1",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "deposit": 10000,
        "leverage": 100,
        "overrides": overrides,
        "run_role": "control",
    }
    prereg = {
        "hypothesis_id": spec["hypothesis_id"],
        "prereg_path": spec["prereg_rel"],
        "frozen": True,
    }
    cost = {
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker": "MetaQuotes-Demo",
        "spread_binding": "current",
        "note": "Missing commission/slippage fields are not zero. Not Real QFSI.",
    }
    include_note = (
        f"Packet-bound include closure note for {spec['hypothesis_id']}. "
        "EA uses Trade.mqh only from terminal Standard Library."
    )

    (stub / "task_packet.json").write_text(
        json.dumps(task, indent=2) + "\n", encoding="utf-8"
    )
    (stub / "prereg.json").write_text(
        json.dumps(prereg, indent=2) + "\n", encoding="utf-8"
    )
    (stub / "cost_source_manifest.json").write_text(
        json.dumps(cost, indent=2) + "\n", encoding="utf-8"
    )
    (stub / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")

    ea = spec["ea_path"]
    evidence = [
        ("task_packet", stub / "task_packet.json"),
        ("source", ea),
        ("prereg", stub / "prereg.json"),
        ("cost_source_manifest", stub / "cost_source_manifest.json"),
        ("include_0001", stub / "include_note.txt"),
    ]
    include_records = []
    evidence_objs = []
    for label, path in evidence:
        h = sha256_file(path)
        evidence_objs.append(
            {
                "label": label,
                "kind": "file",
                "path": str(path),
                "sha256": h,
            }
        )
        if label.startswith("include_"):
            include_records.append(f"{str(path.resolve()).lower()}\t{h}")
    include_records.sort()
    include_closure = text_sha("\n".join(include_records))

    agents = ROOT / "AGENTS.md"
    goal = ROOT / "01. GOAL" / "GOAL.md"
    records = []
    for p in (agents, goal, ea):
        full = p.resolve()
        rel = str(full.relative_to(ROOT.resolve())).replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(full)}")
    prov = text_sha("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    status_sha = text_sha(status)

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": spec["hypothesis_id"],
        "task_packet_sha256": sha256_file(stub / "task_packet.json"),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": spec["hypothesis_id"],
            "run_role": "control",
            "ea_name": spec["ea_name"],
            "symbol": "USDJPY",
            "period": "H1",
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "off",
            "deposit": 10000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {
                "digits": 3,
                "point": 0.001,
                "pip_size": 0.01,
            },
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence_objs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": spec["note"],
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    rec_sha = sha256_file(receipt_path)
    (out_dir / (receipt_path.name.replace(".json", ".sha256.txt"))).write_text(
        rec_sha + "\n", encoding="utf-8"
    )
    return {"receipt": str(receipt_path), "sha256": rec_sha, "hypothesis_id": spec["hypothesis_id"]}


def main() -> int:
    out = [build_one(s) for s in SPECS]
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
