#!/usr/bin/env python3
"""Build NOGIT contract receipts for empty-shelf rebuild trio (PDH-retest/H4/LNY)."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def build(cfg: dict) -> tuple[str, str]:
    ea = ROOT / cfg["ea_rel"]
    prereg = ROOT / cfg["prereg_rel"]
    agents = ROOT / "AGENTS.md"
    goal = ROOT / "01. GOAL/GOAL.md"
    stub_dir = ROOT / cfg["stub_rel"]
    stub_dir.mkdir(parents=True, exist_ok=True)
    contracts = stub_dir.parent

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

    overrides = cfg.get("overrides", "")
    task_packet = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": cfg["hypothesis_id"],
        "ea_name": cfg["ea_name"],
        "symbol": cfg["symbol"],
        "period": cfg["period"],
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": "control",
        "overrides": overrides,
        "note": cfg.get("note", "Empty-shelf rebuild; cost unverified."),
    }
    (stub_dir / "task_packet.json").write_text(
        json.dumps(task_packet, indent=2) + "\n", encoding="utf-8"
    )
    (stub_dir / "prereg.json").write_text(
        json.dumps(
            {
                "hypothesis_id": cfg["hypothesis_id"],
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
        f"{cfg['ea_name']} Trade.mqh standard library stub for include closure.\n",
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
    include_closure_sha256 = sha256_text("\n".join(include_records))

    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": cfg["hypothesis_id"],
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha256,
        "binding": {
            "hypothesis_id": cfg["hypothesis_id"],
            "run_role": "control",
            "ea_name": cfg["ea_name"],
            "symbol": cfg["symbol"],
            "period": cfg["period"],
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "off",
            "deposit": cfg["deposit"],
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": cfg["geometry"],
            "include_closure_sha256": include_closure_sha256,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": cfg.get("note", ""),
    }
    receipt_path = contracts / cfg["receipt_name"]
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (contracts / (cfg["receipt_name"] + ".sha256.txt")).write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(cfg["hypothesis_id"], "RECEIPT_SHA256", receipt_sha)
    return str(receipt_path), receipt_sha


CFGS = [
    {
        "hypothesis_id": "HYP-PDH-RETEST-M15-001",
        "ea_name": "EA_M15PDHRetest",
        "ea_rel": "03. EA Developer/EA_M15PDHRetest/EA_M15PDHRetest.mq5",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_PDH_RETEST_M15_001_PREREG.md",
        "stub_rel": "03. EA Developer/EA_SonicR/research/preflight/pdh_retest_m15/contracts/receipt_stubs_HYP_PDHR_001",
        "receipt_name": "20260714_HYP_PDH_RETEST_M15_001_CONTRACT_RECEIPT.json",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        "overrides": "",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "note": "Empty-shelf rebuild; PDH break then retest; not PDH-BREAK retune.",
    },
    {
        "hypothesis_id": "HYP-H4-STRUCT-BREAK-M15-001",
        "ea_name": "EA_H4StructBreak_M15",
        "ea_rel": "03. EA Developer/EA_H4StructBreak_M15/EA_H4StructBreak_M15.mq5",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_STRUCT_BREAK_M15_001_PREREG.md",
        "stub_rel": "03. EA Developer/EA_SonicR/research/preflight/h4_struct_break_m15/contracts/receipt_stubs_HYP_H4SB_001",
        "receipt_name": "20260714_HYP_H4_STRUCT_BREAK_M15_001_CONTRACT_RECEIPT.json",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        "overrides": "",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "note": "Empty-shelf rebuild; H4 swing BOS + M15 accept; not H1-BOS EMA densify.",
    },
    {
        "hypothesis_id": "HYP-LNY-DUALWIN-M15-001",
        "ea_name": "EA_M15LNYDualWin",
        "ea_rel": "03. EA Developer/EA_M15LNYDualWin/EA_M15LNYDualWin.mq5",
        "prereg_rel": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_LNY_DUALWIN_M15_001_PREREG.md",
        "stub_rel": "03. EA Developer/EA_SonicR/research/preflight/lny_dualwin_m15/contracts/receipt_stubs_HYP_LNY2_001",
        "receipt_name": "20260714_HYP_LNY_DUALWIN_M15_001_CONTRACT_RECEIPT.json",
        "symbol": "USDJPY",
        "period": "M15",
        "deposit": 100000,
        "overrides": "",
        "geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
        "note": "Empty-shelf rebuild; LNY dual-window structural cadence; not day-mine.",
    },
]


if __name__ == "__main__":
    out = {}
    for cfg in CFGS:
        path, sha = build(cfg)
        out[cfg["hypothesis_id"]] = {"path": path, "sha256": sha}
    print(json.dumps(out, indent=2))
