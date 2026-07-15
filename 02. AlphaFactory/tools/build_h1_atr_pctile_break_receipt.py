#!/usr/bin/env python3
"""Build HYP-H1-ATR-PCTILE-BREAK-001 contract receipt."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
ea = ROOT / "03. EA Developer/EA_H1ATRPctileBreak/EA_H1ATRPctileBreak.mq5"
prereg = ROOT / "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_ATR_PCTILE_BREAK_001_PREREG.md"
agents = ROOT / "AGENTS.md"
goal = ROOT / "01. GOAL/GOAL.md"
stub_dir = ROOT / (
    "03. EA Developer/EA_SonicR/research/preflight/"
    "h1_atr_pctile_break/contracts/receipt_stubs_HYP_ATR_PCTILE_001"
)
stub_dir.mkdir(parents=True, exist_ok=True)
contracts = stub_dir.parent


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


prov_paths = [agents, goal, ea]
records = []
root_full = str(ROOT.resolve())
for p in prov_paths:
    full = str(p.resolve())
    rel = full[len(root_full) :].lstrip("\\/").replace("\\", "/")
    records.append(f"{rel}\t{sha256_file(p)}")
prov_sha = sha256_text("\n".join(records))
git_commit = f"NOGIT-{prov_sha}"
git_status_sha256 = sha256_text(
    "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov_sha}"])
)

task_packet = {
    "schema_version": "sonic_research_task_packet.v1",
    "hypothesis_id": "HYP-H1-ATR-PCTILE-BREAK-001",
    "ea_name": "EA_H1ATRPctileBreak",
    "symbol": "USDJPY",
    "period": "H1",
    "from": "2021.01.01",
    "to": "2025.12.31",
    "model": 0,
    "deposit": 100000,
    "leverage": 100,
    "overrides": "",
    "run_role": "control",
    "note": "Wave5 mid-vol ATR%ile Donchian break; cost unverified.",
}
(stub_dir / "task_packet.json").write_text(
    json.dumps(task_packet, indent=2) + "\n", encoding="utf-8"
)
(stub_dir / "prereg.json").write_text(
    json.dumps(
        {
            "hypothesis_id": "HYP-H1-ATR-PCTILE-BREAK-001",
            "prereg_path": str(prereg).replace("\\", "/"),
            "prereg_sha256": sha256_file(prereg),
            "frozen": True,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
(stub_dir / "cost_source_manifest.json").write_text(
    json.dumps(
        {
            "cost_label": "UNVERIFIED_TESTER_DEFAULT",
            "broker": "MetaQuotes-Demo",
            "spread_binding": "current",
            "note": "Missing != 0. Not Real QFSI.",
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
(stub_dir / "include_note.txt").write_text(
    "EA_H1ATRPctileBreak single-file; Trade.mqh MT5 stdlib include closure.\n",
    encoding="utf-8",
)


def file_ev(label: str, path: Path) -> dict:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


evidence = [
    file_ev("task_packet", stub_dir / "task_packet.json"),
    file_ev("source", ea),
    file_ev("prereg", stub_dir / "prereg.json"),
    file_ev("cost_source_manifest", stub_dir / "cost_source_manifest.json"),
    file_ev("include_0001", stub_dir / "include_note.txt"),
]
include_items = [e for e in evidence if e["label"].startswith("include_")]
include_records = []
for item in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
    path = str(Path(item["path"]).resolve()).lower()
    include_records.append(f"{path}\t{item['sha256'].upper()}")
include_closure = sha256_text("\n".join(include_records))

receipt = {
    "schema_version": "sonic_execution_receipt.v1",
    "hypothesis_id": "HYP-H1-ATR-PCTILE-BREAK-001",
    "task_packet_sha256": evidence[0]["sha256"],
    "git_commit": git_commit,
    "git_status_sha256": git_status_sha256,
    "binding": {
        "hypothesis_id": "HYP-H1-ATR-PCTILE-BREAK-001",
        "run_role": "control",
        "ea_name": "EA_H1ATRPctileBreak",
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
    "note": "Wave5 ATR%ile mid-vol Donchian break Model0. Not RR2 densify.",
}
receipt_path = contracts / "20260714_HYP_H1_ATR_PCTILE_BREAK_001_CONTRACT_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
receipt_sha = sha256_file(receipt_path)
(contracts / "20260714_HYP_H1_ATR_PCTILE_BREAK_001_CONTRACT_RECEIPT.sha256.txt").write_text(
    receipt_sha + "\n", encoding="utf-8"
)
print("RECEIPT_SHA256", receipt_sha)
print("SOURCE_SHA256", evidence[1]["sha256"])
print("PATH", receipt_path)
