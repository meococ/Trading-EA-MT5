#!/usr/bin/env python3
"""Build HYP-PORTFOLIO-SB-SPARK-RUNNER-001 contract receipt for EA_SBSparkBook."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
ea = root / "03. EA Developer/EA_SBSparkBook/EA_SBSparkBook.mq5"
sb_mod = root / "03. EA Developer/EA_SBSparkBook/Modules/SB_A1_Module.mqh"
spk_mod = root / "03. EA Developer/EA_SBSparkBook/Modules/SparkAsian_Module.mqh"
agents = root / "AGENTS.md"
goal = root / "01. GOAL/GOAL.md"
prereg = root / (
    "03. EA Developer/EA_SonicR/research/preregs/"
    "20260714_H_PORTFOLIO_SB_SPARK_RUNNER_001_PREREG.md"
)
stub_dir = root / (
    "03. EA Developer/EA_SonicR/research/preflight/"
    "portfolio_sb_spark_runner/contracts/"
    "receipt_stubs_HYP_PORTFOLIO_SB_SPARK_RUNNER_001"
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
root_full = str(root.resolve())
for p in prov_paths:
    full = str(p.resolve())
    if full.lower().startswith(root_full.lower()):
        rel = full[len(root_full) :].lstrip("\\/").replace("\\", "/")
    else:
        rel = full.replace("\\", "/")
    records.append(f"{rel}\t{sha256_file(p)}")
payload = "\n".join(records)
prov_sha = sha256_text(payload)
git_commit = f"NOGIT-{prov_sha}"
status_lines = ["nogit=true", "dirty=true", f"provenance_sha256={prov_sha}"]
git_status_sha256 = sha256_text("\n".join(status_lines))

task_packet = {
    "schema_version": "sonic_research_task_packet.v1",
    "hypothesis_id": "HYP-PORTFOLIO-SB-SPARK-RUNNER-001",
    "ea_name": "EA_SBSparkBook",
    "symbol": "USDJPY",
    "period": "M15",
    "from": "2021.01.01",
    "to": "2025.12.31",
    "model": 0,
    "deposit": 100000,
    "leverage": 100,
    "overrides": "",
    "run_role": "control",
    "sleeve_bindings": {
        "A": "SB A1 weekend-flat baked (002505)",
        "B": "Spark Asian defaults baked (002614)",
    },
    "note": "Dual-sleeve book Model0; magics SB=20260325 SPK=880930; cost unverified.",
}
(stub_dir / "task_packet.json").write_text(
    json.dumps(task_packet, indent=2) + "\n", encoding="utf-8"
)
(stub_dir / "prereg.json").write_text(
    json.dumps(
        {
            "hypothesis_id": "HYP-PORTFOLIO-SB-SPARK-RUNNER-001",
            "prereg_path": str(prereg).replace("\\", "/"),
            "prereg_sha256": sha256_file(prereg),
            "frozen": True,
            "sleeve_runs": ["20260714_002505", "20260714_002614"],
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
            "note": "Missing != 0. Not Real QFSI. Offline compose was proxy only.",
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
(stub_dir / "include_note.txt").write_text(
    "EA_SBSparkBook includes Modules/SB_A1_Module.mqh and Modules/SparkAsian_Module.mqh "
    "as receipt include_* evidence. Trade.mqh is MT5 standard library.\n",
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
    file_ev("include_0002", sb_mod),
    file_ev("include_0003", spk_mod),
]
include_items = [item for item in evidence if item["label"].startswith("include_")]
include_records = []
for item in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
    path = str(Path(item["path"]).resolve()).lower()
    include_records.append(f"{path}\t{item['sha256'].upper()}")
include_closure_sha256 = sha256_text("\n".join(include_records))

receipt = {
    "schema_version": "sonic_execution_receipt.v1",
    "hypothesis_id": "HYP-PORTFOLIO-SB-SPARK-RUNNER-001",
    "task_packet_sha256": evidence[0]["sha256"],
    "git_commit": git_commit,
    "git_status_sha256": git_status_sha256,
    "binding": {
        "hypothesis_id": "HYP-PORTFOLIO-SB-SPARK-RUNNER-001",
        "run_role": "control",
        "ea_name": "EA_SBSparkBook",
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
        "include_closure_sha256": include_closure_sha256,
    },
    "evidence": evidence,
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "note": (
        "Dual-sleeve SB A1 + Spark Asian book. Bindings frozen to 002505/002614. "
        "Model0 requires exclusive tester (no Owner Real terminal64)."
    ),
}
receipt_path = contracts / "20260714_HYP_PORTFOLIO_SB_SPARK_RUNNER_001_CONTRACT_RECEIPT.json"
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
receipt_sha = sha256_file(receipt_path)
(contracts / "20260714_HYP_PORTFOLIO_SB_SPARK_RUNNER_001_CONTRACT_RECEIPT.sha256.txt").write_text(
    receipt_sha + "\n", encoding="utf-8"
)
print("NOGIT", git_commit)
print("status", git_status_sha256)
print("RECEIPT", receipt_path)
print("RECEIPT_SHA256", receipt_sha)
print("SOURCE_SHA256", evidence[1]["sha256"])
print("SB_MOD", evidence[5]["sha256"])
print("SPK_MOD", evidence[6]["sha256"])
