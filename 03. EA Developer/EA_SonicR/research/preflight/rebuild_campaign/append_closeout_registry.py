#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl"
REC = ROOT / "03. EA Developer/EA_SonicR/research/preflight/20260714_STRATEGY_REBUILD_CAMPAIGN_RECEIPT.json"

text = REG.read_text(encoding="utf-8")
rows = []

def maybe(hid: str, run_id: str, row: dict) -> None:
    if run_id in text and hid in text and row["verdict"] in text:
        return
    rows.append(row)

maybe(
    "HYP-SB-MAXKZ2-DENSITY-002",
    "20260714_192304",
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-SB-MAXKZ2-DENSITY-002",
        "state": "parked",
        "parent_candidate": "HYP-SB-WEEKEND-FLAT-001",
        "feature_family": "silverbullet_maxkz2_density",
        "lane": "unlimited_goal_rebuild",
        "setup_type": "MaxTradesPerKZ=2 + A1 weekend-flat",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_MAXKZ2_DENSITY_002_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_SB_MAXKZ2_DENSITY_002_READOUT.md",
        "exact_overrides": "InpMaxTradesPerKZ=2;InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpRiskPct=0.5",
        "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
        "run_ids": ["20260714_192304"],
        "metrics": {
            "trades": 546,
            "pf": 1.334,
            "net": 8123.09,
            "tpw": 2.0942,
            "max_dd_pct": 0.85,
        },
        "validation": {
            "cost_stress": "tester current only",
            "deposit": 100000,
            "research_bar": "HIT_PF_AND_CADENCE_TESTER_ONLY",
        },
        "verdict": "HIT_RESEARCH_BAR_NOT_CONFIRMED",
        "reason": "PF 1.334 / 2.094wk tester; Real QFSI required for GOAL",
        "updated_at": "2026-07-14",
    },
)
maybe(
    "HYP-SB-NYPM-KZ-001",
    "20260714_192203",
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-SB-NYPM-KZ-001",
        "state": "parked",
        "parent_candidate": "HYP-SB-WEEKEND-FLAT-001",
        "feature_family": "silverbullet_nypm_killzone",
        "lane": "unlimited_goal_rebuild",
        "setup_type": "NYPM + A1",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_NYPM_KZ_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_SB_NYPM_KZ_001_READOUT.md",
        "exact_overrides": "InpUseWeekendFlat=1;InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseNYPM=1;InpNYPM_Start=20;InpNYPM_End=22",
        "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
        "run_ids": ["20260714_192203"],
        "metrics": {
            "trades": 635,
            "pf": 1.271,
            "net": 7653.64,
            "tpw": 2.4356,
            "max_dd_pct": 1.05,
        },
        "validation": {"cost_stress": "tester current only", "deposit": 100000},
        "verdict": "PARKED_AT_MODEL_0",
        "reason": "Cadence OK PF short",
        "updated_at": "2026-07-14",
    },
)
maybe(
    "HYP-ITSM-LONDON-ONLY-STRICTALIGN-002",
    "20260714_192116",
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-ITSM-LONDON-ONLY-STRICTALIGN-002",
        "state": "parked",
        "parent_candidate": "HYP-ITSM-PULLBACK-M15-001",
        "feature_family": "m15_itsm_london_only_strictalign",
        "lane": "unlimited_goal_rebuild",
        "setup_type": "London-only + StrictAlign",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_ITSM_LONDON_ONLY_STRICTALIGN_002_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_ITSM_LONDON_ONLY_STRICTALIGN_002_READOUT.md",
        "exact_overrides": "InpUseKZ2=0;InpStrictAlign=1;InpRiskPct=0.5;InpRR_Ratio=2.0;InpMaxTradesDay=2;InpTradeFri=0",
        "source_path": "03. EA Developer/EA_ITSM/EA_ITSM.mq5",
        "run_ids": ["20260714_192116"],
        "metrics": {
            "trades": 482,
            "pf": 1.118,
            "net": 1641.16,
            "tpw": 1.8488,
            "max_dd_pct": 6.96,
        },
        "validation": {"cost_stress": "tester current only"},
        "verdict": "PARKED_AT_MODEL_0",
        "reason": "Loses to NY sibling",
        "updated_at": "2026-07-14",
    },
)

with REG.open("a", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

j = json.loads(REC.read_text(encoding="utf-8"))
j["updated_at_ict"] = "2026-07-14T19:30:00+07:00"
j["closeout"] = "readouts/20260714_STRATEGY_REBUILD_CAMPAIGN_CLOSEOUT.md"
j["best_survivor"] = {
    "hypothesis_id": "HYP-SB-MAXKZ2-DENSITY-002",
    "run_id": "20260714_192304",
    "pf": 1.334,
    "tpw": 2.094,
    "verdict": "HIT_RESEARCH_BAR_NOT_CONFIRMED",
}
REC.write_text(json.dumps(j, indent=2) + "\n", encoding="utf-8")
print("appended", len(rows))
print("receipt updated")
