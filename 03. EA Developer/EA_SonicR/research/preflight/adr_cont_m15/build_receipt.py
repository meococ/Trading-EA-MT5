# -*- coding: utf-8 -*-
"""Build contract receipt + stubs for HYP-ADR-CONT-M15-001."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer" / "EA_M15ADRCont" / "EA_M15ADRCont.mq5"
OUT_DIR = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "adr_cont_m15"
    / "contracts"
)
STUB = OUT_DIR / "receipt_stubs_HYP_ADR_CONT_M15_001"
RECEIPT = OUT_DIR / "20260714_HYP_ADR_CONT_M15_001_CONTRACT_RECEIPT.json"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def text_sha(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STUB.mkdir(parents=True, exist_ok=True)

    overrides = ""
    task = {
        "hypothesis_id": "HYP-ADR-CONT-M15-001",
        "ea_name": "EA_M15ADRCont",
        "symbol": "USDJPY",
        "period": "M15",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "deposit": 10000,
        "leverage": 100,
        "overrides": overrides,
        "run_role": "control",
    }
    prereg = {
        "hypothesis_id": "HYP-ADR-CONT-M15-001",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_ADR_CONT_M15_001_PREREG.md",
        "frozen": True,
    }
    cost = {
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker": "MetaQuotes-Demo",
        "spread_binding": "current",
        "note": "Missing commission/slippage fields are not zero. Not Real QFSI.",
    }
    include_note = (
        "Packet-bound include closure note for HYP-ADR-CONT-M15-001. "
        "EA uses Trade.mqh only from terminal Standard Library."
    )

    (STUB / "task_packet.json").write_text(
        json.dumps(task, indent=2) + "\n", encoding="utf-8"
    )
    (STUB / "prereg.json").write_text(
        json.dumps(prereg, indent=2) + "\n", encoding="utf-8"
    )
    (STUB / "cost_source_manifest.json").write_text(
        json.dumps(cost, indent=2) + "\n", encoding="utf-8"
    )
    (STUB / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")

    evidence = [
        ("task_packet", STUB / "task_packet.json"),
        ("source", EA),
        ("prereg", STUB / "prereg.json"),
        ("cost_source_manifest", STUB / "cost_source_manifest.json"),
        ("include_0001", STUB / "include_note.txt"),
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
    for p in (agents, goal, EA):
        full = p.resolve()
        rel = str(full.relative_to(ROOT.resolve())).replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(full)}")
    prov = text_sha("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    status_sha = text_sha(status)

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": "HYP-ADR-CONT-M15-001",
        "task_packet_sha256": sha256_file(STUB / "task_packet.json"),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": "HYP-ADR-CONT-M15-001",
            "run_role": "control",
            "ea_name": "EA_M15ADRCont",
            "symbol": "USDJPY",
            "period": "M15",
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
        "note": "Model 0 PDH/PDL continuation breakout; opposite of ADRExhaust fade kills; continuation side.",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    rec_sha = sha256_file(RECEIPT)
    (OUT_DIR / "20260714_HYP_ADR_CONT_M15_001_CONTRACT_RECEIPT.sha256.txt").write_text(
        rec_sha + "\n", encoding="utf-8"
    )
    print(json.dumps({"receipt": str(RECEIPT), "sha256": rec_sha, "commit": commit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

