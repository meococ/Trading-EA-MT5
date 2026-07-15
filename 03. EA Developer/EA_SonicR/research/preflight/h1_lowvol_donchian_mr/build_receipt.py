# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer/EA_H1LowVolDonchianMR/EA_H1LowVolDonchianMR.mq5"
OUT = ROOT / "03. EA Developer/EA_SonicR/research/preflight/h1_lowvol_donchian_mr/contracts"
STUB = OUT / "receipt_stubs_HYP_H1_LOWVOL_DONCHIAN_MR_001"
RECEIPT = OUT / "20260714_HYP_H1_LOWVOL_DONCHIAN_MR_001_CONTRACT_RECEIPT.json"
HYP = "HYP-H1-LOWVOL-DONCHIAN-MR-001"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def text_sha(s: str) -> str:
    return sha256_bytes(s.encode())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    STUB.mkdir(parents=True, exist_ok=True)
    overrides = ""
    task = {
        "hypothesis_id": HYP,
        "ea_name": "EA_H1LowVolDonchianMR",
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
        "hypothesis_id": HYP,
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_LOWVOL_DONCHIAN_MR_001_PREREG.md",
        "frozen": True,
    }
    cost = {
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker": "MetaQuotes-Demo",
        "spread_binding": "current",
        "note": "Missing != 0. Not Real QFSI.",
    }
    include_note = "Trade.mqh stdlib only for HYP-H1-LOWVOL-DONCHIAN-MR-001."
    (STUB / "task_packet.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    (STUB / "prereg.json").write_text(json.dumps(prereg, indent=2) + "\n", encoding="utf-8")
    (STUB / "cost_source_manifest.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    (STUB / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")
    evidence = []
    include_records = []
    for label, path in [
        ("task_packet", STUB / "task_packet.json"),
        ("source", EA),
        ("prereg", STUB / "prereg.json"),
        ("cost_source_manifest", STUB / "cost_source_manifest.json"),
        ("include_0001", STUB / "include_note.txt"),
    ]:
        h = sha256_file(path)
        evidence.append({"label": label, "kind": "file", "path": str(path), "sha256": h})
        if label.startswith("include_"):
            include_records.append(f"{str(path.resolve()).lower()}\t{h}")
    include_closure = text_sha("\n".join(sorted(include_records)))
    records = []
    for p in (ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", EA):
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
            "run_role": "control",
            "ea_name": "EA_H1LowVolDonchianMR",
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
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "H1 low-vol Donchian MR; Owner refine mandate unlock.",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    rec_sha = sha256_file(RECEIPT)
    (OUT / "20260714_HYP_H1_LOWVOL_DONCHIAN_MR_001_CONTRACT_RECEIPT.sha256.txt").write_text(
        rec_sha + "\n", encoding="utf-8"
    )
    print(json.dumps({"sha256": rec_sha, "commit": commit}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
