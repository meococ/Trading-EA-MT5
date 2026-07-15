#!/usr/bin/env python3
"""Wave4 registry append: freeze three independent thick+cadence hypotheses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest().upper()


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
    ib = ROOT / "03. EA Developer" / "EA_M15IBOverlapBreak" / "EA_M15IBOverlapBreak.mq5"
    rv = ROOT / "03. EA Developer" / "EA_H1RVCompressBreak" / "EA_H1RVCompressBreak.mq5"
    gj = ROOT / "03. EA Developer" / "EA_H1GBPJPYLead" / "EA_H1GBPJPYLead.mq5"

    rows = [
        row(
            {
                "hypothesis_id": "HYP-M15-IB-OVERLAP-BREAK-001",
                "state": "preregistered",
                "parent_candidate": None,
                "feature_family": "m15_london_ib_overlap_break",
                "lane": "discovery_wave4_20260714",
                "setup_type": "London IB lock → L/NY overlap M15 break; RR=2.5",
                "symbol": "USDJPY",
                "timeframe": "M15",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Wave4 session microstructure; not LondonORB/NYDrive",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_M15_IB_OVERLAP_BREAK_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_M15_IB_OVERLAP_BREAK_001_MODEL0",
                "source_path": "03. EA Developer/EA_M15IBOverlapBreak/EA_M15IBOverlapBreak.mq5",
                "source_hash": sha256(ib),
                "validation": {
                    "cost_stress": "tester current + a priori +$12 if PF>=1.20",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE4_DEDUP_CLEARANCE.md",
                },
                "verdict": "PREREG_FROZEN_WAVE4",
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-H1-RV-COMPRESS-BREAK-001",
                "state": "preregistered",
                "parent_candidate": None,
                "feature_family": "h1_rv_compress_donchian_break",
                "lane": "discovery_wave4_20260714",
                "setup_type": "H1 range-RV compress → Donchian break; RR=2.5",
                "symbol": "USDJPY",
                "timeframe": "H1",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Wave4 vol-normalized breakout; not VolExp/Keltner/NR7",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_RV_COMPRESS_BREAK_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_H1_RV_COMPRESS_BREAK_001_MODEL0",
                "source_path": "03. EA Developer/EA_H1RVCompressBreak/EA_H1RVCompressBreak.mq5",
                "source_hash": sha256(rv),
                "validation": {
                    "cost_stress": "tester current + a priori +$12 if PF>=1.20",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE4_DEDUP_CLEARANCE.md",
                },
                "verdict": "PREREG_FROZEN_WAVE4",
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-GBPJPY-LEAD-USDJPY-H1-001",
                "state": "preregistered",
                "parent_candidate": None,
                "feature_family": "h1_gbpjpy_atr_impulse_lead_usdjpy",
                "lane": "discovery_wave4_20260714",
                "setup_type": "GBPJPY H1 ATR impulse → USDJPY legal lag; RR=2.5",
                "symbol": "USDJPY",
                "timeframe": "H1",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Wave4 cross-asset lag; not GOLDJPY inverse / CrossLead range",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_GBPJPY_LEAD_USDJPY_H1_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_GBPJPY_LEAD_USDJPY_H1_001_MODEL0",
                "source_path": "03. EA Developer/EA_H1GBPJPYLead/EA_H1GBPJPYLead.mq5",
                "source_hash": sha256(gj),
                "validation": {
                    "cost_stress": "tester current + a priori +$12 if PF>=1.20",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE4_DEDUP_CLEARANCE.md",
                },
                "verdict": "PREREG_FROZEN_WAVE4",
            }
        ),
    ]

    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(r["hypothesis_id"], r["state"], r.get("source_hash", "")[:16])

    receipt = {
        "campaign_id": "20260714_DISCOVERY_WAVE4",
        "dedup": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE4_DEDUP_CLEARANCE.md",
        "execute": [
            "HYP-M15-IB-OVERLAP-BREAK-001",
            "HYP-H1-RV-COMPRESS-BREAK-001",
            "HYP-GBPJPY-LEAD-USDJPY-H1-001",
        ],
        "source_hashes": {
            "HYP-M15-IB-OVERLAP-BREAK-001": sha256(ib),
            "HYP-H1-RV-COMPRESS-BREAK-001": sha256(rv),
            "HYP-GBPJPY-LEAD-USDJPY-H1-001": sha256(gj),
        },
    }
    out = (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / "20260714_DISCOVERY_WAVE4_BOOT_RECEIPT.json"
    )
    out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("receipt", out)


if __name__ == "__main__":
    main()
