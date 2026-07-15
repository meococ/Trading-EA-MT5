#!/usr/bin/env python3
"""Append Wave3 Model 0 kill rows to candidate registry."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"

ROWS = [
    {
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
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_OUTSIDE_REV_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H4_OUTSIDE_REV_001_READOUT.md",
        "source_path": "03. EA Developer/EA_H4OutsideRev/EA_H4OutsideRev.mq5",
        "run_ids": ["20260714_221328"],
        "metrics": {
            "trades": 25,
            "pf": 0.773,
            "net": -1136.73,
            "tpw": 0.096,
            "exp": -45.47,
            "dd_pct": 2.38,
        },
        "verdict": "KILLED_AT_MODEL_0",
        "reason": "PF 0.77; N=25<80; tpw~0.10; net negative",
    },
    {
        "hypothesis_id": "HYP-H4-ENGULF-REV-001",
        "state": "killed",
        "parent_candidate": None,
        "feature_family": "h4_body_engulf_reversal_accept",
        "lane": "discovery_wave3_20260714",
        "setup_type": "H4 body-engulf + mid accept; RR=3",
        "symbol": "USDJPY",
        "timeframe": "H4",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_ENGULF_REV_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H4_ENGULF_REV_001_READOUT.md",
        "source_path": "03. EA Developer/EA_H4EngulfRev/EA_H4EngulfRev.mq5",
        "run_ids": ["20260714_231537"],
        "metrics": {
            "trades": 202,
            "pf": 1.131,
            "net": 4886.45,
            "tpw": 0.775,
            "exp": 24.19,
            "dd_pct": 5.67,
        },
        "verdict": "KILLED_AT_MODEL_0",
        "reason": "tpw~0.78<1.0 cadence kill; PF 1.13<1.30; no research HIT",
    },
    {
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
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_PIN_PDLEVEL_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H1_PIN_PDLEVEL_001_READOUT.md",
        "source_path": "03. EA Developer/EA_H1PinPDLevel/EA_H1PinPDLevel.mq5",
        "run_ids": ["20260714_231618"],
        "metrics": {
            "trades": 20,
            "pf": 0.667,
            "net": -567.22,
            "tpw": 0.077,
            "exp": -28.36,
            "dd_pct": 0.79,
        },
        "verdict": "KILLED_AT_MODEL_0",
        "reason": "PF 0.67; N=20<80; tpw~0.08; net negative",
    },
]


def main() -> None:
    base = {
        "record_type": "candidate",
        "schema_version": 1,
        "exact_overrides": "",
        "updated_at": "2026-07-14",
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "source_provenance": (
            "Wave3 Model0 screen; tester server FivePercentOnline-Real; "
            "not full QFSI / not GOAL"
        ),
        "validation": {
            "cost_stress": "skipped_not_research_HIT",
            "dedup": "readouts/20260714_DISCOVERY_WAVE3_DEDUP_CLEARANCE.md",
            "partial_real_reprice": "not_run_no_HIT",
        },
    }
    with REG.open("a", encoding="utf-8") as f:
        for row in ROWS:
            obj = dict(base)
            obj.update(row)
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            print(row["hypothesis_id"], row["verdict"])


if __name__ == "__main__":
    main()
