# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def text_sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def build(h: str, ea_name: str, ea_rel: str, folder: str, prereg_name: str, note: str) -> None:
    ea = ROOT / ea_rel
    out = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / folder / "contracts"
    stub = out / f"receipt_stubs_{h.replace('-', '_')}"
    receipt_path = out / f"20260714_{h.replace('-', '_')}_CONTRACT_RECEIPT.json"
    out.mkdir(parents=True, exist_ok=True)
    stub.mkdir(parents=True, exist_ok=True)
    overrides = ""
    task = {
        "hypothesis_id": h,
        "ea_name": ea_name,
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
        "hypothesis_id": h,
        "prereg_path": f"03. EA Developer/EA_SonicR/research/preregs/{prereg_name}",
        "frozen": True,
    }
    cost = {
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker": "MetaQuotes-Demo",
        "spread_binding": "current",
        "note": "Missing commission/slippage fields are not zero. Not Real QFSI.",
    }
    include_note = (
        f"Packet-bound include closure note for {h}. "
        "EA uses Trade.mqh only from terminal Standard Library."
    )
    (stub / "task_packet.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    (stub / "prereg.json").write_text(json.dumps(prereg, indent=2) + "\n", encoding="utf-8")
    (stub / "cost_source_manifest.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    (stub / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")

    evidence = [
        ("task_packet", stub / "task_packet.json"),
        ("source", ea),
        ("prereg", stub / "prereg.json"),
        ("cost_source_manifest", stub / "cost_source_manifest.json"),
        ("include_0001", stub / "include_note.txt"),
    ]
    evidence_objs = []
    include_records = []
    for label, path in evidence:
        digest = sha256_file(path)
        evidence_objs.append({"label": label, "kind": "file", "path": str(path), "sha256": digest})
        if label.startswith("include_"):
            include_records.append(f"{str(path.resolve()).lower()}\t{digest}")
    include_records.sort()
    include_closure = text_sha("\n".join(include_records))

    records = []
    for p in (ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", ea):
        full = p.resolve()
        rel = str(full.relative_to(ROOT.resolve())).replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(full)}")
    prov = text_sha("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    status_sha = text_sha(status)

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": h,
        "task_packet_sha256": sha256_file(stub / "task_packet.json"),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": h,
            "run_role": "control",
            "ea_name": ea_name,
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
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence_objs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    rec_sha = sha256_file(receipt_path)
    (out / receipt_path.name.replace(".json", ".sha256.txt")).write_text(rec_sha + "\n", encoding="utf-8")
    print(json.dumps({"hypothesis_id": h, "receipt": str(receipt_path), "sha256": rec_sha}, indent=2))


def main() -> int:
    build(
        "HYP-FAILED-ORB-FADE-M15-001",
        "EA_M15FailedORBFade",
        "03. EA Developer/EA_M15FailedORBFade/EA_M15FailedORBFade.mq5",
        "failed_orb_fade_m15",
        "20260714_H_FAILED_ORB_FADE_M15_001_PREREG.md",
        "Model 0 London failed-auction OR fade; opposite of LondonORB break.",
    )
    build(
        "HYP-EMA-STRETCH-FADE-M15-001",
        "EA_M15EMAStretchFade",
        "03. EA Developer/EA_M15EMAStretchFade/EA_M15EMAStretchFade.mq5",
        "ema_stretch_fade_m15",
        "20260714_H_EMA_STRETCH_FADE_M15_001_PREREG.md",
        "Model 0 EMA stretch mean-reversion; not ADR/ChopMR/ORB.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
