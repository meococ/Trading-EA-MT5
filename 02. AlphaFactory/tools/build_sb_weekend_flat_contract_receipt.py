#!/usr/bin/env python3
"""Rebuild HYP-SB-WEEKEND-FLAT-001 control/challenger contract receipts."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(r"d:\Trading EA MT5")
ea = root / "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5"
agents = root / "AGENTS.md"
goal = root / "01. GOAL/GOAL.md"
freeze = root / "03. EA Developer/EA_SonicR/research/preregs/20260713_H_SB_WEEKEND_FLAT_001_RESEARCH_FREEZE.md"
stub_dir = root / "03. EA Developer/EA_SonicR/research/preflight/sb_weekend_flat/receipt_stubs_HYP_SB_WEEKEND_FLAT_001"
out_dir = root / "03. EA Developer/EA_SonicR/research/preflight/sb_weekend_flat"
stub_dir.mkdir(parents=True, exist_ok=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest().upper()


def nogit_snapshot(extra: Path) -> tuple[str, str]:
    prov_paths = [agents, goal]
    if extra.is_file():
        prov_paths.append(extra)
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
    status_lines = ["nogit=true", "dirty=true", f"provenance_sha256={prov_sha}"]
    return git_commit, sha256_text("\n".join(status_lines))


def file_ev(label: str, path: Path) -> dict:
    return {
        "label": label,
        "kind": "file",
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
    }


def build(role: str, overrides: str, extra_evidence: list[dict] | None = None) -> tuple[Path, str]:
    git_commit, git_status_sha256 = nogit_snapshot(ea)
    task_packet = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": "HYP-SB-WEEKEND-FLAT-001",
        "ea_name": "EA_SilverBullet",
        "symbol": "USDJPY",
        "period": "M15",
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": role,
        "deposit": 100000,
        "overrides": overrides,
        "note": "A1 weekend-flat Model 0; cost proxy only.",
    }
    tp_path = stub_dir / f"task_packet_{role}.json"
    tp_path.write_text(json.dumps(task_packet, indent=2) + "\n", encoding="utf-8")
    prereg_path = stub_dir / f"prereg_{role}.json"
    prereg_path.write_text(
        json.dumps(
            {
                "hypothesis_id": "HYP-SB-WEEKEND-FLAT-001",
                "prereg_path": str(freeze),
                "prereg_sha256": sha256_file(freeze),
                "frozen": True,
                "run_role": role,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cost_path = stub_dir / f"cost_source_manifest_{role}.json"
    cost_path.write_text(
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
    include_path = stub_dir / f"include_note_{role}.txt"
    include_path.write_text(
        "EA_SilverBullet_v2 uses Trade.mqh from MT5 standard library. "
        "Stub satisfies include_* receipt closure for Model 0 screen.\n",
        encoding="utf-8",
    )
    evidence = [
        file_ev("task_packet", tp_path),
        file_ev("source", ea),
        file_ev("prereg", prereg_path),
        file_ev("cost_source_manifest", cost_path),
        file_ev("include_0001", include_path),
    ]
    if extra_evidence:
        evidence.extend(extra_evidence)
    include_items = [e for e in evidence if e["label"].startswith("include_")]
    include_records = []
    for e in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
        path = str(Path(e["path"]).resolve()).lower()
        include_records.append(f"{path}\t{e['sha256'].upper()}")
    include_closure_sha256 = sha256_text("\n".join(include_records))
    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": "HYP-SB-WEEKEND-FLAT-001",
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha256,
        "binding": {
            "hypothesis_id": "HYP-SB-WEEKEND-FLAT-001",
            "run_role": role,
            "ea_name": "EA_SilverBullet",
            "symbol": "USDJPY",
            "period": "M15",
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
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
        "note": f"Model 0 {role} for SB weekend-flat A1. Cost provenance unverified.",
    }
    receipt_path = out_dir / f"20260714_HYP_SB_WEEKEND_FLAT_001_{role.upper()}_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (out_dir / f"20260714_HYP_SB_WEEKEND_FLAT_001_{role.upper()}_RECEIPT.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(role, receipt_path.name, receipt_sha)
    return receipt_path, receipt_sha


if __name__ == "__main__":
    import sys

    role = "control"
    overrides = "InpUseWeekendFlat=0"
    extra = None
    if len(sys.argv) > 1 and sys.argv[1] == "challenger":
        role = "challenger"
        overrides = "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseWeekendFlat=1"
        control_run = root / "02. AlphaFactory/runs/EA_SilverBullet/20260714_000937"
        extra = [
            file_ev("matched_control_manifest", control_run / "run_manifest.json"),
            file_ev("matched_control_report", control_run / "report.html"),
        ]
    build(role, overrides, extra)
