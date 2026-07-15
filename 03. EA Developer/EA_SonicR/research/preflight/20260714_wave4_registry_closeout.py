#!/usr/bin/env python3
"""Append Wave4 Model 0 park/kill registry rows."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
SHA = json.loads(
    (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / "20260714_WAVE4_REPORT_SHA.json"
    ).read_text(encoding="utf-8")
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    rows = [
        {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": "HYP-M15-IB-OVERLAP-BREAK-001",
            "state": "parked",
            "parent_candidate": None,
            "feature_family": "m15_london_ib_overlap_break",
            "lane": "discovery_wave4_20260714",
            "setup_type": "London IB → L/NY overlap M15 break; RR=2.5",
            "symbol": "USDJPY",
            "timeframe": "M15",
            "window": "2021.01.01-2025.12.31",
            "model": 0,
            "source_provenance": "Wave4 Model 0",
            "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_M15_IB_OVERLAP_BREAK_001_PREREG.md",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_M15_IB_OVERLAP_BREAK_001_READOUT.md",
            "exact_overrides": "",
            "variant_tag": "HYP_M15_IB_OVERLAP_BREAK_001_MODEL0",
            "source_path": "03. EA Developer/EA_M15IBOverlapBreak/EA_M15IBOverlapBreak.mq5",
            "source_hash": sha256_file(
                ROOT / "03. EA Developer" / "EA_M15IBOverlapBreak" / "EA_M15IBOverlapBreak.mq5"
            ),
            "run_ids": ["20260714_223618"],
            "metrics": {
                "trades": 987,
                "trades_per_elapsed_week": 3.79,
                "pf": 1.05,
                "net": 5582.77,
                "expectancy": 5.66,
            },
            "validation": {
                "status": "PARKED_WEAK_PF",
                "cost_stress": "base+$12 x1 PF 0.94 FAIL",
                "report_sha256": SHA["20260714_223618"],
            },
            "verdict": "PARK",
            "updated_at": "2026-07-14",
            "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        },
        {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": "HYP-H1-RV-COMPRESS-BREAK-001",
            "state": "killed",
            "parent_candidate": None,
            "feature_family": "h1_rv_compress_donchian_break",
            "lane": "discovery_wave4_20260714",
            "setup_type": "H1 range-RV compress → Donchian break; RR=2.5",
            "symbol": "USDJPY",
            "timeframe": "H1",
            "window": "2021.01.01-2025.12.31",
            "model": 0,
            "source_provenance": "Wave4 Model 0",
            "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_RV_COMPRESS_BREAK_001_PREREG.md",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H1_RV_COMPRESS_BREAK_001_READOUT.md",
            "exact_overrides": "",
            "variant_tag": "HYP_H1_RV_COMPRESS_BREAK_001_MODEL0",
            "source_path": "03. EA Developer/EA_H1RVCompressBreak/EA_H1RVCompressBreak.mq5",
            "source_hash": sha256_file(
                ROOT / "03. EA Developer" / "EA_H1RVCompressBreak" / "EA_H1RVCompressBreak.mq5"
            ),
            "run_ids": ["20260714_223714"],
            "metrics": {
                "trades": 84,
                "trades_per_elapsed_week": 0.32,
                "pf": 1.61,
                "net": 4825.99,
                "expectancy": 57.45,
            },
            "validation": {
                "status": "KILLED_AT_MODEL_0_CADENCE",
                "cost_stress": "base+$12 x1.5 PF 1.38 PASS / x2 1.32 PASS diagnostic only",
                "report_sha256": SHA["20260714_223714"],
            },
            "verdict": "KILL",
            "reason": "tpw ~0.32 outside [1,6]; thick friction not sole GOAL book",
            "updated_at": "2026-07-14",
            "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        },
        {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": "HYP-GBPJPY-LEAD-USDJPY-H1-001",
            "state": "parked",
            "parent_candidate": None,
            "feature_family": "h1_gbpjpy_atr_impulse_lead_usdjpy",
            "lane": "discovery_wave4_20260714",
            "setup_type": "GBPJPY H1 ATR impulse → USDJPY legal lag; RR=2.5",
            "symbol": "USDJPY",
            "timeframe": "H1",
            "window": "2021.01.01-2025.12.31",
            "model": 0,
            "source_provenance": "Wave4 Model 0",
            "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_GBPJPY_LEAD_USDJPY_H1_001_PREREG.md",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_GBPJPY_LEAD_USDJPY_H1_001_READOUT.md",
            "exact_overrides": "",
            "variant_tag": "HYP_GBPJPY_LEAD_USDJPY_H1_001_MODEL0",
            "source_path": "03. EA Developer/EA_H1GBPJPYLead/EA_H1GBPJPYLead.mq5",
            "source_hash": sha256_file(
                ROOT / "03. EA Developer" / "EA_H1GBPJPYLead" / "EA_H1GBPJPYLead.mq5"
            ),
            "run_ids": ["20260714_223748"],
            "metrics": {
                "trades": 1337,
                "trades_per_elapsed_week": 5.13,
                "pf": 1.10,
                "net": 12638.81,
                "expectancy": 9.45,
            },
            "validation": {
                "status": "PARKED_WEAK_PF",
                "cost_stress": "base+$12 x1 PF 0.98 FAIL",
                "report_sha256": SHA["20260714_223748"],
            },
            "verdict": "PARK",
            "updated_at": "2026-07-14",
            "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        },
    ]
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(r["hypothesis_id"], r["state"], r["verdict"])


if __name__ == "__main__":
    main()
