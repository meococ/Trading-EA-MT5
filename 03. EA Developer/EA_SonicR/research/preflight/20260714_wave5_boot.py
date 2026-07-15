#!/usr/bin/env python3
"""Wave5: build contract receipts + registry boot for three hypotheses."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def text_sha(s: str) -> str:
    return sha256_bytes(s.encode())


def build_receipt(
    *,
    hyp: str,
    ea_name: str,
    ea_rel: str,
    period: str,
    symbol: str,
    stub_dir: Path,
    receipt_path: Path,
    digits: int,
    point: float,
    pip_size: float,
    note: str,
) -> str:
    stub_dir.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    ea = ROOT / ea_rel
    overrides = ""
    task = {
        "hypothesis_id": hyp,
        "ea_name": ea_name,
        "symbol": symbol,
        "period": period,
        "from": "2021.01.01",
        "to": "2025.12.31",
        "model": 0,
        "deposit": 100000,
        "leverage": 100,
        "overrides": overrides,
        "run_role": "control",
    }
    prereg = {
        "hypothesis_id": hyp,
        "frozen": True,
        "wave": "discovery_wave5_20260714",
    }
    cost = {
        "cost_label": "UNVERIFIED_TESTER_DEFAULT",
        "broker": "MetaQuotes-Demo",
        "spread_binding": "current",
        "note": "Missing != 0. Not Real QFSI.",
    }
    include_note = f"Trade.mqh stdlib only for {hyp}."
    (stub_dir / "task_packet.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    (stub_dir / "prereg.json").write_text(json.dumps(prereg, indent=2) + "\n", encoding="utf-8")
    (stub_dir / "cost_source_manifest.json").write_text(json.dumps(cost, indent=2) + "\n", encoding="utf-8")
    (stub_dir / "include_note.txt").write_text(include_note + "\n", encoding="utf-8")

    evidence = []
    include_records = []
    for label, path in [
        ("task_packet", stub_dir / "task_packet.json"),
        ("source", ea),
        ("prereg", stub_dir / "prereg.json"),
        ("cost_source_manifest", stub_dir / "cost_source_manifest.json"),
        ("include_0001", stub_dir / "include_note.txt"),
    ]:
        h = sha256_file(path)
        evidence.append({"label": label, "kind": "file", "path": str(path), "sha256": h})
        if label.startswith("include_"):
            include_records.append(f"{str(path.resolve()).lower()}\t{h}")
    include_closure = text_sha("\n".join(sorted(include_records)))
    records = []
    for p in (ROOT / "AGENTS.md", ROOT / "01. GOAL" / "GOAL.md", ea):
        full = p.resolve()
        rel = str(full.relative_to(ROOT.resolve())).replace("\\", "/")
        records.append(f"{rel}\t{sha256_file(full)}")
    prov = text_sha("\n".join(records))
    commit = f"NOGIT-{prov}"
    status_sha = text_sha("\n".join(["nogit=true", "dirty=true", f"provenance_sha256={prov}"]))
    receipt = {
        "schema_version": "sonic_execution_receipt.v1",
        "hypothesis_id": hyp,
        "task_packet_sha256": sha256_file(stub_dir / "task_packet.json"),
        "git_commit": commit,
        "git_status_sha256": status_sha,
        "binding": {
            "hypothesis_id": hyp,
            "run_role": "control",
            "ea_name": ea_name,
            "symbol": symbol,
            "period": period,
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
            "symbol_geometry": {"digits": digits, "point": point, "pip_size": pip_size},
            "include_closure_sha256": include_closure,
        },
        "evidence": evidence,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return sha256_file(receipt_path)


def row(obj: dict) -> dict:
    base = {
        "record_type": "candidate",
        "schema_version": 1,
        "readout_path": None,
        "run_ids": [],
        "metrics": None,
        "updated_at": "2026-07-14",
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
    }
    base.update(obj)
    return base


def main() -> None:
    specs = [
        {
            "hyp": "HYP-H1-ATR-PCTILE-BREAK-001",
            "ea_name": "EA_H1ATRPctileBreak",
            "ea_rel": "03. EA Developer/EA_H1ATRPctileBreak/EA_H1ATRPctileBreak.mq5",
            "period": "H1",
            "symbol": "USDJPY",
            "family": "h1_atr_percentile_donchian_break",
            "setup": "H1 Donchian break only ATR%ile[40,70]; RR=2.5",
            "prereg": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_ATR_PCTILE_BREAK_001_PREREG.md",
            "digits": 3,
            "point": 0.001,
            "pip_size": 0.01,
            "stub": PRE / "h1_atr_pctile_break" / "contracts" / "receipt_stubs_HYP_ATRP_001",
            "receipt": PRE
            / "h1_atr_pctile_break"
            / "contracts"
            / "20260714_HYP_H1_ATR_PCTILE_BREAK_001_CONTRACT_RECEIPT.json",
            "note": "Wave5 Model 0; mid ATR%ile Donchian break RR=2.5",
        },
        {
            "hyp": "HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001",
            "ea_name": "EA_EURUSD_H1AsiaBoxLondonBreak",
            "ea_rel": "03. EA Developer/EA_EURUSD_H1AsiaBoxLondonBreak/EA_EURUSD_H1AsiaBoxLondonBreak.mq5",
            "period": "H1",
            "symbol": "EURUSD",
            "family": "eurusd_h1_asia_box_london_break",
            "setup": "EURUSD Asia box→London break + ATR%ile mid; RR=2.5",
            "prereg": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_EURUSD_H1_ASIA_BOX_LONDON_BREAK_001_PREREG.md",
            "digits": 5,
            "point": 0.00001,
            "pip_size": 0.0001,
            "stub": PRE / "eurusd_h1_asia_box" / "contracts" / "receipt_stubs_HYP_ABLB_001",
            "receipt": PRE
            / "eurusd_h1_asia_box"
            / "contracts"
            / "20260714_HYP_EURUSD_H1_ASIA_BOX_LONDON_BREAK_001_CONTRACT_RECEIPT.json",
            "note": "Wave5 Model 0; EURUSD Asia-box London break RR=2.5",
        },
        {
            "hyp": "HYP-M15-NY-IB-DRIVE-BREAK-001",
            "ea_name": "EA_M15NYIBDriveBreak",
            "ea_rel": "03. EA Developer/EA_M15NYIBDriveBreak/EA_M15NYIBDriveBreak.mq5",
            "period": "M15",
            "symbol": "USDJPY",
            "family": "m15_ny_ib_drive_break",
            "setup": "NY IB [13,14) → drive break [14,17); RR=2.5",
            "prereg": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_M15_NY_IB_DRIVE_BREAK_001_PREREG.md",
            "digits": 3,
            "point": 0.001,
            "pip_size": 0.01,
            "stub": PRE / "m15_ny_ib_drive" / "contracts" / "receipt_stubs_HYP_NYIB_001",
            "receipt": PRE
            / "m15_ny_ib_drive"
            / "contracts"
            / "20260714_HYP_M15_NY_IB_DRIVE_BREAK_001_CONTRACT_RECEIPT.json",
            "note": "Wave5 Model 0; NY IB drive break RR=2.5",
        },
    ]

    contracts = []
    hashes = {}
    rows = []
    for s in specs:
        rec_sha = build_receipt(
            hyp=s["hyp"],
            ea_name=s["ea_name"],
            ea_rel=s["ea_rel"],
            period=s["period"],
            symbol=s["symbol"],
            stub_dir=s["stub"],
            receipt_path=s["receipt"],
            digits=s["digits"],
            point=s["point"],
            pip_size=s["pip_size"],
            note=s["note"],
        )
        src_hash = sha256_file(ROOT / s["ea_rel"])
        hashes[s["hyp"]] = src_hash
        contracts.append(
            {
                "hypothesis_id": s["hyp"],
                "ea_name": s["ea_name"],
                "period": s["period"],
                "symbol": s["symbol"],
                "deposit": 100000,
                "receipt": str(s["receipt"]),
                "receipt_sha256": rec_sha,
            }
        )
        rows.append(
            row(
                {
                    "hypothesis_id": s["hyp"],
                    "state": "preregistered",
                    "parent_candidate": None,
                    "feature_family": s["family"],
                    "lane": "discovery_wave5_20260714",
                    "setup_type": s["setup"],
                    "symbol": s["symbol"],
                    "timeframe": s["period"],
                    "window": "2021.01.01-2025.12.31",
                    "model": 0,
                    "source_provenance": "Wave5 joint thick+cadence; de-dup cleared",
                    "prereg_path": s["prereg"],
                    "exact_overrides": "",
                    "variant_tag": s["hyp"].replace("-", "_") + "_MODEL0",
                    "source_path": s["ea_rel"],
                    "source_hash": src_hash,
                    "validation": {
                        "cost_stress": "tester current + a priori +$12 if PF>=1.20",
                        "dedup": "readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md",
                    },
                    "verdict": "PREREG_FROZEN_WAVE5",
                }
            )
        )
        print(s["hyp"], "receipt", rec_sha[:16], "src", src_hash[:16])

    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    boot = {
        "campaign_id": "20260714_DISCOVERY_WAVE5",
        "dedup": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE5_DEDUP_CLEARANCE.md",
        "phase0_freeze": "03. EA Developer/EA_SonicR/research/readouts/20260714_PHASE0_RR2_SPARK_UNIVERSE_FREEZE.md",
        "execute": [s["hyp"] for s in specs],
        "source_hashes": hashes,
    }
    (PRE / "20260714_DISCOVERY_WAVE5_BOOT_RECEIPT.json").write_text(
        json.dumps(boot, indent=2) + "\n", encoding="utf-8"
    )
    (PRE / "20260714_DISCOVERY_WAVE5_CONTRACTS.json").write_text(
        json.dumps(contracts, indent=2) + "\n", encoding="utf-8"
    )
    print("boot+contracts written")


if __name__ == "__main__":
    main()
