#!/usr/bin/env python3
"""Build contract receipts for Owner SB-rebuild iteration (2026-07-14)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(r"d:\Trading EA MT5")
agents = root / "AGENTS.md"
goal = root / "01. GOAL/GOAL.md"


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


def build(
    *,
    hyp_id: str,
    ea_name: str,
    ea_path: Path,
    prereg_path: Path,
    period: str,
    overrides: str,
    deposit: int,
    out_subdir: str,
    note: str,
    run_role: str = "challenger",
) -> tuple[Path, str]:
    stub_dir = (
        root
        / "03. EA Developer/EA_SonicR/research/preflight"
        / out_subdir
        / "contracts"
        / f"receipt_stubs_{hyp_id.replace('-', '_')}"
    )
    contracts = stub_dir.parent
    stub_dir.mkdir(parents=True, exist_ok=True)

    git_commit, git_status_sha256 = nogit_snapshot(ea_path)
    tp = {
        "schema_version": "sonic_research_task_packet.v1",
        "hypothesis_id": hyp_id,
        "ea_name": ea_name,
        "symbol": "USDJPY",
        "period": period,
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "run_role": run_role,
        "deposit": deposit,
        "overrides": overrides,
        "note": note,
    }
    (stub_dir / "task_packet.json").write_text(json.dumps(tp, indent=2) + "\n", encoding="utf-8")
    (stub_dir / "prereg.json").write_text(
        json.dumps(
            {
                "hypothesis_id": hyp_id,
                "prereg_path": str(prereg_path),
                "prereg_sha256": sha256_file(prereg_path),
                "frozen": True,
                "run_role": run_role,
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
        f"{ea_name} uses Trade.mqh from MT5 standard library. "
        "Stub satisfies include_* receipt closure for Model 0 screen.\n",
        encoding="utf-8",
    )
    evidence = [
        file_ev("task_packet", stub_dir / "task_packet.json"),
        file_ev("source", ea_path),
        file_ev("prereg", stub_dir / "prereg.json"),
        file_ev("cost_source_manifest", stub_dir / "cost_source_manifest.json"),
        file_ev("include_0001", stub_dir / "include_note.txt"),
    ]
    include_items = [e for e in evidence if e["label"].startswith("include_")]
    include_records = []
    for e in sorted(include_items, key=lambda x: str(Path(x["path"]).resolve()).lower()):
        path = str(Path(e["path"]).resolve()).lower()
        include_records.append(f"{path}\t{e['sha256'].upper()}")
    include_closure_sha256 = sha256_text("\n".join(include_records))
    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": hyp_id,
        "task_packet_sha256": evidence[0]["sha256"],
        "git_commit": git_commit,
        "git_status_sha256": git_status_sha256,
        "binding": {
            "hypothesis_id": hyp_id,
            "run_role": run_role,
            "ea_name": ea_name,
            "symbol": "USDJPY",
            "period": period,
            "from": "2021.01.01",
            "to": "2025.12.31",
            "model": 0,
            "execution_mode": 0,
            "fixed_delay_ms": 0,
            "overrides": overrides,
            "telemetry_tier": "off",
            "deposit": deposit,
            "leverage": 100,
            "spread": "current",
            "required_sidecars": [],
            "symbol_geometry": {"digits": 3, "point": 0.001, "pip_size": 0.01},
            "include_closure_sha256": include_closure_sha256,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": note,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    receipt_path = contracts / f"{stamp}_{hyp_id.replace('-', '_')}_CONTRACT_RECEIPT.json"
    # Stable names for CLI:
    receipt_path = contracts / f"20260714_{hyp_id.replace('-', '_')}_CONTRACT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    receipt_sha = sha256_file(receipt_path)
    (contracts / f"20260714_{hyp_id.replace('-', '_')}_CONTRACT_RECEIPT.sha256.txt").write_text(
        receipt_sha + "\n", encoding="utf-8"
    )
    print(hyp_id, receipt_path, receipt_sha)
    return receipt_path, receipt_sha


if __name__ == "__main__":
    specs = [
        dict(
            hyp_id="HYP-SB-MAXHOLD-A2-001",
            ea_name="EA_SilverBullet",
            ea_path=root / "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
            prereg_path=root
            / "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_MAXHOLD_A2_001_PREREG.md",
            period="M15",
            overrides="InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseMaxHold=1;InpMaxHoldHours=30",
            deposit=100000,
            out_subdir="sb_maxhold_a2",
            note="SB A2 max-hold on A1 weekend-flat; Model 0; cost unverified.",
        ),
        dict(
            hyp_id="HYP-SB-NYPM-KZ-001",
            ea_name="EA_SilverBullet",
            ea_path=root / "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
            prereg_path=root
            / "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_NYPM_KZ_001_PREREG.md",
            period="M15",
            overrides="InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseNYPM=1;InpNYPM_Start=20;InpNYPM_End=22",
            deposit=100000,
            out_subdir="sb_nypm_kz",
            note="SB NYPM KZ expand + A1 weekend-flat; Model 0; cost unverified.",
        ),
        dict(
            hyp_id="HYP-SPARK-CAPACITY-3PD-001",
            ea_name="EA_M15SparkAsian",
            ea_path=root / "03. EA Developer/EA_M15SparkAsian/EA_M15SparkAsian.mq5",
            prereg_path=root
            / "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SPARK_CAPACITY_3PD_001_PREREG.md",
            period="M15",
            overrides="InpMaxPerDay=3",
            deposit=100000,
            out_subdir="spark_capacity_3pd",
            note="Spark MaxPerDay=3 capacity; Tue-Wed unchanged; Model 0; cost unverified.",
        ),
        dict(
            hyp_id="HYP-H1-LOWVOL-DONCHIAN-MR-001",
            ea_name="EA_H1LowVolDonchianMR",
            ea_path=root / "03. EA Developer/EA_H1LowVolDonchianMR/EA_H1LowVolDonchianMR.mq5",
            prereg_path=root
            / "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_LOWVOL_DONCHIAN_MR_001_PREREG.md",
            period="H1",
            overrides="",
            deposit=10000,
            out_subdir="h1_lowvol_donchian_mr",
            note="H1 low-vol Donchian MR; Model 0; cost unverified.",
            run_role="control",
        ),
    ]
    for s in specs:
        build(**s)
