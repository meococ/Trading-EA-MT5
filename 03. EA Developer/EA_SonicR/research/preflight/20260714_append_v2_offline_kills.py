#!/usr/bin/env python3
"""Append structural rebuild V2 offline kill rows to candidate registry."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
SHA = "10F0A23A85A2D8307C56F63DE080899FF340D9D57D1C5811DAC1514149B455D0"
READOUT = "03. EA Developer/EA_SonicR/research/readouts/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V2.md"

ROWS = [
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H1-PDLIQ-STOPRUN-ACCEPT-001",
        "state": "killed",
        "verdict": "OFFLINE_KILL",
        "reason": "offline N=164 PF=1.11 tpw=0.63; cadence+pf+x1.5 stress fail; no Model0",
        "updated_at": "2026-07-14",
        "lane": "structural_rebuild_offline_v2_20260714",
        "feature_family": "h1_pdliq_stoprun_multibar_accept",
        "symbol": "USDJPY",
        "timeframe": "H1",
        "window": "2021.01.01-2025.12.31",
        "model": "offline_closed_bar_probe",
        "source_path": None,
        "prereg_path": None,
        "readout_path": READOUT,
        "run_ids": [],
        "metrics": {
            "n": 164,
            "pf": 1.1115,
            "net": 5501.15,
            "exp": 33.5436,
            "tpw": 0.629,
        },
        "validation": {
            "offline_probe": "KILL",
            "model0": "WITHHELD_KILL_FAST",
            "cost_x1_5_pf": 1.0498,
        },
        "receipt_sha256": SHA,
    },
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-LNY-RANGE-ACCEPT-M15-001",
        "state": "killed",
        "verdict": "OFFLINE_KILL",
        "reason": "offline N=4 PF=0 expansion_days=13; event starves; n+cadence+pf+stress fail; no Model0",
        "updated_at": "2026-07-14",
        "lane": "structural_rebuild_offline_v2_20260714",
        "feature_family": "lny_london_range_accept_break",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": "offline_closed_bar_probe",
        "source_path": None,
        "prereg_path": None,
        "readout_path": READOUT,
        "run_ids": [],
        "metrics": {
            "n": 4,
            "pf": 0.0,
            "net": -606.82,
            "exp": -151.705,
            "tpw": 0.0153,
        },
        "validation": {
            "offline_probe": "KILL",
            "model0": "WITHHELD_KILL_FAST",
            "funnel_expansion_days": 13,
        },
        "receipt_sha256": SHA,
    },
]


def main() -> None:
    existing = REG.read_text(encoding="utf-8")
    with REG.open("a", encoding="utf-8") as f:
        for r in ROWS:
            if r["hypothesis_id"] in existing:
                print("skip", r["hypothesis_id"])
                continue
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print("appended", r["hypothesis_id"], r["verdict"])


if __name__ == "__main__":
    main()
