# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer" / "EA_M15NYOpenDrive" / "EA_M15NYOpenDrive.mq5"
OUT_DIR = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "ny_open_drive_m15" / "contracts"
STUB = OUT_DIR / "receipt_stubs_HYP_NY_OPEN_DRIVE_M15_001"
RECEIPT = OUT_DIR / "20260714_HYP_NY_OPEN_DRIVE_M15_001_CONTRACT_RECEIPT.json"
H = "HYP-NY-OPEN-DRIVE-M15-001"
EA_NAME = "EA_M15NYOpenDrive"

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()

def text_sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STUB.mkdir(parents=True, exist_ok=True)
    overrides = ""
    task = {"hypothesis_id": H, "ea_name": EA_NAME, "symbol": "USDJPY", "period": "M15", "from": "2021.01.01", "to": "2025.12.31", "model": 0, "deposit": 10000, "leverage": 100, "overrides": overrides, "run_role": "control"}
    prereg = {"hypothesis_id": H, "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_NY_OPEN_DRIVE_M15_001_PREREG.md", "frozen": True}
    cost = {"cost_label": "UNVERIFIED_TESTER_DEFAULT", "broker": "MetaQuotes-Demo", "spread_binding": "current", "note": "Missing commission/slippage fields are not zero. Not Real QFSI."}
    include_note = f"Packet-bound include closure note for {H}. EA uses Trade.mqh only from terminal Standard Library."
    (STUB / "task_packet.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    (STUB / "prereg.json").write_text(json.dumps(prereg, indent=2) + "\n", encoding="utf-8")
    (STUB / "cost_source_manifest.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    (STUB / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")
    evidence = [("task_packet", STUB / "task_packet.json"), ("source", EA), ("prereg", STUB / "prereg.json"), ("cost_source_manifest", STUB / "cost_source_manifest.json"), ("include_0001", STUB / "include_note.txt")]
    evidence_objs = []
    include_records = []
    for label, path in evidence:
        h = sha256_file(path)
        evidence_objs.append({"label": label, "kind": "file", "path": str(path), "sha256": h})
        if label.startswith("include_"):
            include_records.append(f"{str(path.resolve()).lower()}\t{h}")
    include_records.sort()
    include_closure = text_sha("\n".join(include_records))
    records = []
    for p in (ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", EA):
        full = p.resolve()
        rel = str(full.relative_to(ROOT.resolve())).replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(full)}")
    prov = text_sha("\n".join(records))
    commit = f"NOGIT-{prov}"
    status = "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"])
    status_sha = text_sha(status)
    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": H,
        "task_packet_sha256": sha256_file(STUB / "task_packet.json"),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": H, "run_role": "control", "ea_name": EA_NAME, "symbol": "USDJPY", "period": "M15",
            "from": "2021.01.01", "to": "2025.12.31", "model": 0, "execution_mode": 0, "fixed_delay_ms": 0,
            "overrides": overrides, "telemetry_tier": "off", "deposit": 10000, "leverage": 100, "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence_objs,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Model 0 NY opening-range drive; independent of LondonORB/Spark/PDH.",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    rec_sha = sha256_file(RECEIPT)
    (OUT_DIR / "20260714_HYP_NY_OPEN_DRIVE_M15_001_CONTRACT_RECEIPT.sha256.txt").write_text(rec_sha + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(RECEIPT), "sha256": rec_sha}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
