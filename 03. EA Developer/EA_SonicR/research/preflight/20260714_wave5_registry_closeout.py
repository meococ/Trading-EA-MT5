#!/usr/bin/env python3
"""Append Wave5 Model 0 park/kill registry rows."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
MET = json.loads(
    (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / "20260714_WAVE5_MODEL0_METRICS.json"
    ).read_text(encoding="utf-8")
)
SHA = json.loads(
    (
        ROOT
        / "03. EA Developer"
        / "EA_SonicR"
        / "research"
        / "preflight"
        / "20260714_WAVE5_REPORT_SHA.json"
    ).read_text(encoding="utf-8")
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    by_id = {r["hypothesis_id"]: r for r in MET}
    specs = [
        {
            "hypothesis_id": "HYP-H1-ATR-PCTILE-BREAK-001",
            "state": "parked",
            "feature_family": "h1_atr_percentile_donchian_break",
            "setup_type": "H1 Donchian break only ATR%ile[40,70]; RR=2.5",
            "symbol": "USDJPY",
            "timeframe": "H1",
            "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_ATR_PCTILE_BREAK_001_PREREG.md",
            "source_path": "03. EA Developer/EA_H1ATRPctileBreak/EA_H1ATRPctileBreak.mq5",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE5_ATR_ASIA_NYIB_CLOSEOUT.md",
            "verdict": "PARK",
            "status": "PARKED_WEAK_PF",
        },
        {
            "hypothesis_id": "HYP-EURUSD-H1-ASIA-BOX-LONDON-BREAK-001",
            "state": "killed",
            "feature_family": "eurusd_h1_asia_box_london_break",
            "setup_type": "EURUSD Asia box→London break + ATR%ile mid; RR=2.5",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_EURUSD_H1_ASIA_BOX_LONDON_BREAK_001_PREREG.md",
            "source_path": "03. EA Developer/EA_EURUSD_H1AsiaBoxLondonBreak/EA_EURUSD_H1AsiaBoxLondonBreak.mq5",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE5_ATR_ASIA_NYIB_CLOSEOUT.md",
            "verdict": "KILL",
            "status": "KILLED_PF_BELOW_1",
        },
        {
            "hypothesis_id": "HYP-M15-NY-IB-DRIVE-BREAK-001",
            "state": "parked",
            "feature_family": "m15_ny_ib_drive_break",
            "setup_type": "NY IB [13,14) → drive break [14,17); RR=2.5",
            "symbol": "USDJPY",
            "timeframe": "M15",
            "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_M15_NY_IB_DRIVE_BREAK_001_PREREG.md",
            "source_path": "03. EA Developer/EA_M15NYIBDriveBreak/EA_M15NYIBDriveBreak.mq5",
            "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE5_ATR_ASIA_NYIB_CLOSEOUT.md",
            "verdict": "PARK",
            "status": "PARKED_WEAK_PF",
        },
    ]
    rows = []
    for s in specs:
        m = by_id[s["hypothesis_id"]]
        rid = m["run_id"]
        cs = m["cost_stress_base_plus_12"]
        rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": s["hypothesis_id"],
                "state": s["state"],
                "parent_candidate": None,
                "feature_family": s["feature_family"],
                "lane": "discovery_wave5_20260714",
                "setup_type": s["setup_type"],
                "symbol": s["symbol"],
                "timeframe": s["timeframe"],
                "window": "2021.01.01-2025.12.31",
                "model": 0,
                "source_provenance": "Wave5 Model 0",
                "prereg_path": s["prereg_path"],
                "readout_path": s["readout_path"],
                "exact_overrides": "",
                "variant_tag": s["hypothesis_id"].replace("-", "_") + "_MODEL0",
                "source_path": s["source_path"],
                "source_hash": sha256_file(ROOT / s["source_path"]),
                "run_ids": [rid],
                "metrics": {
                    "trades": m["trades"],
                    "trades_per_elapsed_week": m["tpw_elapsed"],
                    "pf": m["pf"],
                    "net": m["net"],
                    "expectancy": m["expectancy"],
                },
                "validation": {
                    "status": s["status"],
                    "cost_stress": (
                        f"base+$12 x1 {cs['x1']} / x1.5 {cs['x1_5']} / x2 {cs['x2']}"
                    ),
                    "report_sha256": SHA[rid],
                },
                "verdict": s["verdict"],
                "updated_at": "2026-07-14",
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
            }
        )

    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(r["hypothesis_id"], r["state"], r["run_ids"][0])


if __name__ == "__main__":
    main()
