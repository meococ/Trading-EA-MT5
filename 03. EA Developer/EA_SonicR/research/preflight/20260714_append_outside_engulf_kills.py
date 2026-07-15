#!/usr/bin/env python3
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


rows = [
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H4-OUTSIDE-REV-001",
        "state": "killed",
        "parent_candidate": "THICK_EDGE_WAVE_EMPTY_stub",
        "feature_family": "h4_outside_bar_reversal_fade",
        "lane": "discovery_wave3_20260714",
        "setup_type": "H4 outside+WR7 failed-expansion fade; RR=3",
        "symbol": "USDJPY",
        "timeframe": "H4",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Model 0 kill after offline probe; opposite NR7",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_OUTSIDE_REV_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H4_OUTSIDE_REV_001_READOUT.md",
        "exact_overrides": "",
        "variant_tag": "HYP_H4_OUTREV_001_MODEL0",
        "source_path": "03. EA Developer/EA_H4OutsideRev/EA_H4OutsideRev.mq5",
        "source_hash": sha(ROOT / "03. EA Developer" / "EA_H4OutsideRev" / "EA_H4OutsideRev.mq5"),
        "run_ids": ["20260714_221504"],
        "metrics": {"n": 25, "pf": 0.7732, "tpw": 0.0959, "exp": -45.47, "net": -1136.73},
        "validation": {
            "status": "KILLED_AT_MODEL_0",
            "cost_stress": "analysis/cost_stress_base12.json",
            "offline_probe": "preflight/20260714_H4_OUTSIDE_REV_OFFLINE_PROBE.json",
            "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
        },
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "verdict": "KILLED_AT_MODEL_0",
        "updated_at": "2026-07-14",
    },
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H4-ENGULF-REV-001",
        "state": "killed",
        "parent_candidate": None,
        "feature_family": "h4_body_engulf_reversal_accept",
        "lane": "discovery_wave3_20260714",
        "setup_type": "H4 body-engulf + mid accept; RR=3; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "H4",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Second thick-edge after OutsideRev kill; not M15 EngulfTrend",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_ENGULF_REV_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H4_ENGULF_REV_001_READOUT.md",
        "exact_overrides": "",
        "variant_tag": "HYP_H4_ENGULF_REV_001_MODEL0",
        "source_path": "03. EA Developer/EA_H4EngulfRev/EA_H4EngulfRev.mq5",
        "source_hash": sha(ROOT / "03. EA Developer" / "EA_H4EngulfRev" / "EA_H4EngulfRev.mq5"),
        "run_ids": ["20260714_221546"],
        "metrics": {"n": 202, "pf": 1.1309, "tpw": 0.7748, "exp": 24.19, "net": 4886.45},
        "validation": {
            "status": "KILLED_AT_MODEL_0",
            "cost_stress": "analysis/cost_stress_base12.json",
            "offline_probe": "preflight/20260714_H4_ENGULF_REV_OFFLINE_PROBE.json",
            "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
        },
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "verdict": "KILLED_AT_MODEL_0",
        "updated_at": "2026-07-14",
    },
]

with REG.open("a", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(r["hypothesis_id"], r["verdict"], r["run_ids"][0])

receipt = {
    "campaign_id": "20260714_THICK_EDGE_OUTSIDE_ENGULF",
    "closeout": "03. EA Developer/EA_SonicR/research/readouts/20260714_THICK_EDGE_OUTSIDE_ENGULF_CLOSEOUT.md",
    "results": [
        {
            "hypothesis_id": "HYP-H4-OUTSIDE-REV-001",
            "run_id": "20260714_221504",
            "verdict": "KILL",
            "pf": 0.7732,
            "n": 25,
            "tpw": 0.0959,
        },
        {
            "hypothesis_id": "HYP-H4-ENGULF-REV-001",
            "run_id": "20260714_221546",
            "verdict": "KILL",
            "pf": 1.1309,
            "n": 202,
            "tpw": 0.7748,
        },
    ],
    "next_legal": "HYP-H1-PIN-PDLEVEL-001",
    "updated_at": datetime.now().isoformat(timespec="seconds"),
}
out = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_THICK_EDGE_OUTSIDE_ENGULF_RECEIPT.json"
)
out.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("receipt", out)
