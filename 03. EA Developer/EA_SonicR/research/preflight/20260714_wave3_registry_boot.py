#!/usr/bin/env python3
"""Wave3 registry append: intake-kill clones + freeze three independents."""
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
    out_rev = ROOT / "03. EA Developer" / "EA_H4OutsideRev" / "EA_H4OutsideRev.mq5"
    engulf = ROOT / "03. EA Developer" / "EA_H4EngulfRev" / "EA_H4EngulfRev.mq5"
    pin = ROOT / "03. EA Developer" / "EA_H1PinPDLevel" / "EA_H1PinPDLevel.mq5"

    rows = [
        row(
            {
                "hypothesis_id": "HYP-ITSM-NYONLY-RR3-THICK-001",
                "state": "killed",
                "parent_candidate": "HYP-ITSM-NYONLY-STRICTALIGN-002",
                "feature_family": "m15_itsm_nyonly_rr3_thick",
                "lane": "discovery_wave3_20260714",
                "setup_type": "INTAKE_KILL Wave3 — RR spam of parked ITSM NY",
                "symbol": "USDJPY",
                "timeframe": "M15",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Owner Wave3 ban RR clones",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_ITSM_NYONLY_RR3_THICK_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_ITSM_NYONLY_RR3_THICK_001_INTAKE_KILL",
                "source_path": "03. EA Developer/EA_ITSM/EA_ITSM.mq5",
                "validation": {
                    "status": "KILLED_AT_INTAKE",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
                },
                "verdict": "KILLED_AT_INTAKE",
                "reason": "RR stretch clone banned for Wave3",
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-SB-MAXKZ2-PARTIAL-R1-001",
                "state": "killed",
                "parent_candidate": "HYP-SB-MAXKZ2-DENSITY-002",
                "feature_family": "silverbullet_maxkz2_partial_exit",
                "lane": "discovery_wave3_20260714",
                "setup_type": "INTAKE_KILL Wave3 — MaxKZ2 family clone",
                "symbol": "USDJPY",
                "timeframe": "M15",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Owner Wave3 ban MaxKZ clones",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_MAXKZ2_PARTIAL_R1_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_SB_MAXKZ2_PARTIAL_R1_001_INTAKE_KILL",
                "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
                "validation": {
                    "status": "KILLED_AT_INTAKE",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
                },
                "verdict": "KILLED_AT_INTAKE",
                "reason": "MaxKZ clone banned for Wave3",
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-H4-OUTSIDE-REV-001",
                "state": "preregistered",
                "parent_candidate": "THICK_EDGE_WAVE_EMPTY_stub",
                "feature_family": "h4_outside_bar_reversal_fade",
                "lane": "discovery_wave3_20260714",
                "setup_type": "H4 outside+WR7 failed-expansion fade; RR=3",
                "symbol": "USDJPY",
                "timeframe": "H4",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Wave3 execute frozen stub; opposite NR7",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_OUTSIDE_REV_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_H4_OUTREV_001_MODEL0",
                "source_path": "03. EA Developer/EA_H4OutsideRev/EA_H4OutsideRev.mq5",
                "source_hash": sha256(out_rev),
                "validation": {
                    "cost_stress": "tester current + a priori +$12 if PF>=1.20",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
                },
                "verdict": "PREREG_FROZEN_WAVE3",
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-H4-ENGULF-REV-001",
                "state": "preregistered",
                "parent_candidate": None,
                "feature_family": "h4_body_engulf_reversal_accept",
                "lane": "discovery_wave3_20260714",
                "setup_type": "H4 body-engulf + mid accept; RR=3; Mon-Thu",
                "symbol": "USDJPY",
                "timeframe": "H4",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Wave3 independent; not M15 EngulfTrend",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_ENGULF_REV_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_H4_ENGULF_REV_001_MODEL0",
                "source_path": "03. EA Developer/EA_H4EngulfRev/EA_H4EngulfRev.mq5",
                "source_hash": sha256(engulf),
                "validation": {
                    "cost_stress": "tester current + a priori +$12 if PF>=1.20",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
                },
                "verdict": "PREREG_FROZEN",
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-H1-PIN-PDLEVEL-001",
                "state": "preregistered",
                "parent_candidate": None,
                "feature_family": "h1_pin_prior_day_level_fade",
                "lane": "discovery_wave3_20260714",
                "setup_type": "H1 pin wick at prior D1 HL fade; RR=3; Mon-Thu",
                "symbol": "USDJPY",
                "timeframe": "H1",
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Wave3 independent; not PDH M15 / H1SFP densify",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_PIN_PDLEVEL_001_PREREG.md",
                "exact_overrides": "",
                "variant_tag": "HYP_H1_PIN_PDLEVEL_001_MODEL0",
                "source_path": "03. EA Developer/EA_H1PinPDLevel/EA_H1PinPDLevel.mq5",
                "source_hash": sha256(pin),
                "validation": {
                    "cost_stress": "tester current + a priori +$12 if PF>=1.20",
                    "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
                },
                "verdict": "PREREG_FROZEN",
            }
        ),
    ]

    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(r["hypothesis_id"], r["state"], r.get("source_hash", "")[:16])

    receipt = {
        "campaign_id": "20260714_DISCOVERY_WAVE3",
        "dedup": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
        "intake_kills": [
            "HYP-ITSM-NYONLY-RR3-THICK-001",
            "HYP-SB-MAXKZ2-PARTIAL-R1-001",
        ],
        "execute": [
            "HYP-H4-OUTSIDE-REV-001",
            "HYP-H4-ENGULF-REV-001",
            "HYP-H1-PIN-PDLEVEL-001",
        ],
        "source_hashes": {
            "HYP-H4-OUTSIDE-REV-001": sha256(out_rev),
            "HYP-H4-ENGULF-REV-001": sha256(engulf),
            "HYP-H1-PIN-PDLEVEL-001": sha256(pin),
        },
    }
    out = (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / "20260714_DISCOVERY_WAVE3_BOOT_RECEIPT.json"
    )
    out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("receipt", out)


if __name__ == "__main__":
    main()
