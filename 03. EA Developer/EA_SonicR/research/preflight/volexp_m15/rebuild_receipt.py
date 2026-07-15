from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(r"d:\Trading EA MT5")
EA = ROOT / "03. EA Developer" / "EA_M15VolExpansion" / "EA_M15VolExpansion.mq5"
STUBS = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "volexp_m15"
    / "contracts"
    / "receipt_stubs_HYP_VOLEXP_M15_001"
)
RECEIPT = STUBS.parent / "20260713_HYP_VOLEXP_M15_001_CONTRACT_RECEIPT.json"
PREREG = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preregs"
    / "20260713_H_VOLEXP_M15_001_PREREG.md"
)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest().upper()


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT.resolve()).as_posix()


paths = [ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", EA]
records = [f"{rel(p)}\t{sha256_file(p)}" for p in paths]
prov = sha256_text("\n".join(records))
git_commit = f"NOGIT-{prov}"
status_lines = ["nogit=true", "dirty=true", f"provenance_sha256={prov}"]
git_status_sha256 = sha256_text("\n".join(status_lines))

STUBS.mkdir(parents=True, exist_ok=True)
task = {
    "schema_version": "sonic_research_task_packet.v1",
    "hypothesis_id": "HYP-VOLEXP-M15-001",
    "ea_name": "EA_M15VolExpansion",
    "symbol": "USDJPY",
    "period": "M15",
    "from": "2021.01.01",
    "to": "2025.12.31",
    "model": 0,
    "run_role": "control",
    "note": "First Model 0 screen under Owner unlimited-GOAL; cost not broker-verified.",
}
(STUBS / "task_packet.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
(STUBS / "prereg.json").write_text(
    json.dumps({"hypothesis_id": "HYP-VOLEXP-M15-001", "prereg_path": str(PREREG)}, indent=2)
    + "\n",
    encoding="utf-8",
)
(STUBS / "cost_source_manifest.json").write_text(
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
inc = STUBS / "include_note.txt"
if not inc.exists():
    inc.write_text(
        "EA_M15VolExpansion is single-file; Trade.mqh is MT5 standard library. "
        "This stub satisfies include_* receipt closure for Model 0 screen.\n",
        encoding="utf-8",
    )

evidence = [
    {
        "label": "task_packet",
        "kind": "file",
        "path": str(STUBS / "task_packet.json"),
        "sha256": sha256_file(STUBS / "task_packet.json"),
    },
    {"label": "source", "kind": "file", "path": str(EA), "sha256": sha256_file(EA)},
    {
        "label": "prereg",
        "kind": "file",
        "path": str(STUBS / "prereg.json"),
        "sha256": sha256_file(STUBS / "prereg.json"),
    },
    {
        "label": "cost_source_manifest",
        "kind": "file",
        "path": str(STUBS / "cost_source_manifest.json"),
        "sha256": sha256_file(STUBS / "cost_source_manifest.json"),
    },
    {
        "label": "include_0001",
        "kind": "file",
        "path": str(inc),
        "sha256": sha256_file(inc),
    },
]
include_evidence = [e for e in evidence if e["label"].startswith("include_")]
include_records = []
for e in sorted(include_evidence, key=lambda x: x["path"]):
    p = str(Path(e["path"]).resolve()).lower()
    include_records.append(f"{p}\t{e['sha256'].upper()}")
include_closure = sha256_text("\n".join(include_records))

receipt = {
    "schema_version": "sonic_execution_receipt.v1",
    "hypothesis_id": "HYP-VOLEXP-M15-001",
    "task_packet_sha256": evidence[0]["sha256"],
    "git_commit": git_commit,
    "git_status_sha256": git_status_sha256,
    "binding": {
        "hypothesis_id": "HYP-VOLEXP-M15-001",
        "run_role": "control",
        "ea_name": "EA_M15VolExpansion",
        "symbol": "USDJPY",
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
        "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "include_closure_sha256": include_closure,
    },
    "evidence": evidence,
    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "note": (
        "Model 0 control screen for vol-expansion M15. Binding must match "
        "alpha.ps1 invocation. Cost provenance unverified. NOGIT refreshed 2026-07-14."
    ),
}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print("RECEIPT", RECEIPT)
print("RECEIPT_SHA256", sha256_file(RECEIPT))
print("GIT_COMMIT", git_commit)
print("SOURCE", evidence[1]["sha256"])
