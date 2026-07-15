# -*- coding: utf-8 -*-
from pathlib import Path
import json, hashlib

reg = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\CANDIDATE_REGISTRY.jsonl")
row = {
    "record_type": "candidate",
    "schema_version": 1,
    "hypothesis_id": "HYP-SB-MAXHOLD-A2-001",
    "state": "parked",
    "parent_candidate": "HYP-SB-WEEKEND-FLAT-001",
    "feature_family": "silverbullet_management",
    "lane": "unlimited_goal_sb_mgmt",
    "setup_type": "A1 weekend-flat + MaxHold 30h",
    "symbol": "USDJPY",
    "timeframe": "M15",
    "window": "2021.01.01-2025.12.31",
    "model": 0,
    "source_provenance": "Owner refine mandate 2026-07-14",
    "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_SB_MAXHOLD_A2_001_PREREG.md",
    "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_SB_MAXHOLD_A2_001_READOUT.md",
    "exact_overrides": "InpFridayFlatHour=21;InpFridayFlatMinute=45;InpMaxHoldHours=30;InpUseMaxHold=1;InpUseWeekendFlat=1",
    "variant_tag": "HYP_SB_MAXHOLD_A2_001_MODEL0",
    "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
    "run_ids": ["20260714_191628"],
    "matched_control_run_id": "20260714_002505",
    "metrics": {
        "trades": 521,
        "pf": 1.334,
        "net": 7540.77,
        "tpw": 1.998,
        "max_dd_pct": 0.85,
        "expectancy": 14.47,
    },
    "validation": {"cost_stress": "tester current only", "vs_a1": "non_destructive"},
    "verdict": "park",
    "reason": "PF 1.334 / tpw 1.998; non-destructive vs A1; GOAL unmet; mgmt budget 2/2",
    "updated_at": "2026-07-14",
}
with reg.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
print("ok", row["hypothesis_id"], row["state"])
