#!/usr/bin/env python3
"""Build HYP-SPARK-ASIAN-GBPUSD-001 contract receipt."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
ea = root / "03. EA Developer/EA_M15SparkAsianGB/EA_M15SparkAsianGB.mq5"
agents = root / "AGENTS.md"
goal = root / "01. GOAL/GOAL.md"
prereg = root / "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SPARK_ASIAN_GBPUSD_001_PREREG.md"
stub_dir = root / "03. EA Developer/EA_SonicR/research/preflight/spark_asian_gb/contracts/receipt_stubs_HYP_SPARK_ASIAN_GBPUSD_001"
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


prov_paths = [agents, goal]
if ea.is_file():
    prov_paths.append(ea)
records = []
root_full = str(root.resolve())
for p in prov_paths:
    full = str(p.resolve())
    if full.lower().startswith(root_full.lower()):
        rel = full[len(root_full) :].lstrip("\\/").replace("\\", "/")
    else:
        rel = full.replace("\\", "/")
    records.append(f"{rel}\t{sha256_file(p)}")
prov_sha = sha256_text("\n".join(records))
git_commit = f"NOGIT-{prov_sha}"
git_status_sha256 = sha256_text(
    "\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov_sha}"])
)

task_packet = {
    "schema_version": "sonic_research_task_packet.v1",
    "hypothesis_id": "HYP-SPARK-ASIAN-GBPUSD-001",
    "ea_name": "EA_M15SparkAsianGB",
    "symbol": "GBPUSD",
    "period": "M15",
    "from": "2021.01.01",
    "to": "2025.12.31",
    "model": 0,
    "run_role": "control",
    "note": "Symbol-transfer child of SparkAsian; S107 seed; cost unverified.",
}
(stub_dir / "task_packet.json").write_text(json.dumps(task_packet, indent=2) + "\n", encoding="utf-8")
(stub_dir / "prereg.json").write_text(
    json.dumps(
        {
            "hypothesis_id": "HYP-SPARK-ASIAN-GBPUSD-001",
            "prereg_path": str(prereg),
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
            "cost_provenance": "UNVERIFIED",
            "spread_policy": "tester_current",
            "commission": "unknown_not_zero",
            "slippage": "unknown_not_zero",
            "note": "Model 0 screen only; missing cost != 0.",
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
(stub_dir / "include_note.txt").write_text(
    "EA_M15SparkAsianGB is single-file; Trade.mqh is MT5 standard library.\n",
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
include_items = [item for item in evidence if item["label"].startswith("include_")]
include_records = []
for item in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
    path = str(Path(item["path"]).resolve()).lower()
    include_records.append(f"{path}\t{item['sha256'].upper()}")
include_closure_sha256 = sha256_text("\n".join(include_records))

receipt = {
    "schema_version": "sonic_execution_receipt.v1",
    "hypothesis_id": "HYP-SPARK-ASIAN-GBPUSD-001",
    "task_packet_sha256": evidence[0]["sha256"],
    "git_commit": git_commit,
    "git_status_sha256": git_status_sha256,
    "binding": {
        "hypothesis_id": "HYP-SPARK-ASIAN-GBPUSD-001",
        "run_role": "control",
        "ea_name": "EA_M15SparkAsianGB",
        "symbol": "GBPUSD",
        "period": "M15",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": "",
        "telemetry_tier": "off",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": [],
        "symbol_geometry": {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
        "include_closure_sha256": include_closure_sha256,
    },
    "evidence": evidence,
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "note": "SparkAsian GBPUSD symbol child. Not Mon-Thu USDJPY rescue.",
}
receipt_path = contracts / "20260714_HYP_SPARK_ASIAN_GBPUSD_001_CONTRACT_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
receipt_sha = sha256_file(receipt_path)
print("RECEIPT_SHA256", receipt_sha)
print("SOURCE_SHA256", evidence[1]["sha256"])
(contracts / "20260714_HYP_SPARK_ASIAN_GBPUSD_001_CONTRACT_RECEIPT.sha256.txt").write_text(
    receipt_sha + "\n", encoding="utf-8"
)
