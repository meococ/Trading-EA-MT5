#!/usr/bin/env python3
"""Append kill rows for PIN Model0 + THREEBAR offline probe."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"

rows = [
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H1-PIN-PDLEVEL-001",
        "state": "killed",
        "parent_candidate": None,
        "feature_family": "h1_pin_prior_day_level_fade",
        "lane": "discovery_wave3_20260714",
        "setup_type": "H1 pin at prior D1 HL fade; RR=3",
        "symbol": "USDJPY",
        "timeframe": "H1",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Authoritative Model0 closeout confirm for parent CONTINUE",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_PIN_PDLEVEL_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H1_PIN_PDLEVEL_001_READOUT.md",
        "exact_overrides": "",
        "variant_tag": "HYP_H1_PIN_PDLEVEL_001_MODEL0",
        "source_path": "03. EA Developer/EA_H1PinPDLevel/EA_H1PinPDLevel.mq5",
        "run_ids": ["20260714_221912"],
        "metrics": {
            "trades": 20,
            "pf": 0.667,
            "net": -567.22,
            "tpw": 0.077,
            "max_dd_pct": 0.79,
            "expectancy": -28.36,
        },
        "validation": {
            "cost_stress": "skipped_pf_lt_1.20",
            "status": "KILLED_AT_MODEL_0_CONFIRMED",
        },
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "verdict": "KILLED_AT_MODEL_0",
        "updated_at": "2026-07-14",
    },
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H1-THREEBAR-REV-001",
        "state": "killed",
        "parent_candidate": "HYP-H1-PIN-PDLEVEL-001",
        "feature_family": "h1_three_bar_reversal",
        "lane": "post_pin_thick_edge_20260714",
        "setup_type": "H1 classic 3-bar rev; MinBodyFrac 0.35; RR=3; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "H1",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Killed at offline probe; Model0 withheld",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_THREEBAR_REV_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H1_THREEBAR_REV_001_READOUT.md",
        "exact_overrides": "",
        "variant_tag": "HYP_H1_THREEBAR_REV_001_OFFLINE",
        "source_path": "03. EA Developer/EA_H1ThreeBarRev/EA_H1ThreeBarRev.mq5",
        "run_ids": [],
        "metrics": {
            "trades": 1741,
            "pf": 1.037,
            "net": 16271.83,
            "tpw": 6.678,
            "expectancy": 9.35,
            "pf_cost_x1": 0.99,
            "pf_cost_x1_5": 0.967,
            "pf_cost_x2": 0.945,
        },
        "validation": {
            "offline_probe": "preflight/20260714_H1_THREEBAR_REV_OFFLINE_PROBE.json",
            "status": "KILLED_AT_OFFLINE_PROBE",
            "model0": "NOT_RUN_FAIL_CLOSED",
        },
        "cost_grade": "UNVERIFIED_SYNTHETIC_PLUS_REPORT_ONLY_12",
        "verdict": "KILLED_AT_OFFLINE_PROBE",
        "updated_at": "2026-07-14",
    },
]

def main() -> None:
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(r["hypothesis_id"], r["verdict"])


if __name__ == "__main__":
    main()
