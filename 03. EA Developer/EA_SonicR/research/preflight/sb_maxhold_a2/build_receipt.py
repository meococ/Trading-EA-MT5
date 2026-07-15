# -*- coding: utf-8 -*-
"""Contract receipt for HYP-SB-MAXHOLD-A2-001."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5"
OUT = ROOT / "03. EA Developer/EA_SonicR/research/preflight/sb_maxhold_a2/contracts"
STUB = OUT / "receipt_stubs_HYP_SB_MAXHOLD_A2_001"
RECEIPT = OUT / "20260714_HYP_SB_MAXHOLD_A2_001_CONTRACT_RECEIPT.json"
HYP = "HYP-SB-MAXHOLD-A2-001"
# Alphabetical key order matches alpha.ps1 Sort-Object
OVERRIDES = (
    "InpFridayFlatHour=21;InpFridayFlatMinute=45;"
    "InpMaxHoldHours=30;InpUseMaxHold=1;InpUseWeekendFlat=1"
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def text_sha(s: str) -> str:
    return sha256_bytes(s.encode("utf-8"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    STUB.mkdir(parents=True, exist_ok=True)
    task = {
        "hypothesis_id": HYP,
        "ea_name": "EA_SilverBullet",
        "symbol": "USDJPY",
        "period": "M15",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "deposit": 100000,
        "leverage": 100,
        "overrides": OVERRIDES,
        "run_role": "challenger",
    }
    prereg = {
        "hypothesis_id": HYP,
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_MAXHOLD_A2_001_PREREG.md",
        "frozen": True,
    }
    cost = {
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker": "MetaQuotes-Demo",
        "spread_binding": "current",
        "note": "Missing commission/slippage fields are not zero. Not Real QFSI.",
    }
    include_note = "EA_SilverBullet_v2 Trade.mqh stdlib only. MaxHold A2 management child."
    (STUB / "task_packet.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    (STUB / "prereg.json").write_text(json.dumps(prereg, indent=2) + "\n", encoding="utf-8")
    (STUB / "cost_source_manifest.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    (STUB / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")

    evidence = [
        ("task_packet", STUB / "task_packet.json"),
        ("source", EA),
        ("prereg", STUB / "prereg.json"),
        ("cost_source_manifest", STUB / "cost_source_manifest.json"),
        ("include_0001", STUB / "include_note.txt"),
    ]
    evidence_objs = []
    include_records = []
    for label, path in evidence:
        h = sha256_file(path)
        evidence_objs.append({"label": label, "kind": "file", "path": str(path), "sha256": h})
        if label.startswith("include_"):
            include_records.append(f"{str(path.resolve()).lower()}\t{h}")

    # Matched baseline = parked A1 weekend-flat challenger (management stack parent)
    ctrl_manifest = (
        ROOT
        / "02. AlphaFactory/runs/EA_SilverBullet/20260714_002505/run_manifest.json"
    )
    ctrl_report = (
        ROOT / "02. AlphaFactory/runs/EA_SilverBullet/20260714_002505/report.html"
    )
    for label, path in (
        ("matched_control_manifest", ctrl_manifest),
        ("matched_control_report", ctrl_report),
    ):
        h = sha256_file(path)
        evidence_objs.append(
            {"label": label, "kind": "file", "path": str(path.resolve()), "sha256": h}
        )

    include_closure = text_sha("\n".join(sorted(include_records)))

    agents = ROOT / "AGENTS.md"
    goal = ROOT / "01. GOAL" / "GOAL.md"
    records = []
    for p in (agents, goal, EA):
        full = p.resolve()
        rel = str(full.relative_to(ROOT.resolve())).replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(full)}")
    prov = text_sha("\n".join(records))
    commit = f"NOGIT-{prov}"
    status_sha = text_sha("\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"]))

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": HYP,
        "task_packet_sha256": sha256_file(STUB / "task_packet.json"),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": HYP,
            "run_role": "challenger",
            "ea_name": "EA_SilverBullet",
            "symbol": "USDJPY",
            "period": "M15",
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": OVERRIDES,
            "telemetry_tier": "off",
            "deposit": 100000,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence_objs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "MaxHold A2 stacked on A1 weekend-flat; offline probe non-destructive proxy.",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    rec_sha = sha256_file(RECEIPT)
    (OUT / "20260714_HYP_SB_MAXHOLD_A2_001_CONTRACT_RECEIPT.sha256.txt").write_text(
        rec_sha + "\n", encoding="utf-8"
    )
    print(json.dumps({"receipt": str(RECEIPT), "sha256": rec_sha, "commit": commit, "overrides": OVERRIDES}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
