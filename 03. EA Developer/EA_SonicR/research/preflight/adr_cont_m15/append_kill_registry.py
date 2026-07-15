# -*- coding: utf-8 -*-
from pathlib import Path
import json

reg = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\CANDIDATE_REGISTRY.jsonl")
row = {
    "record_type": "candidate",
    "schema_version": 1,
    "hypothesis_id": "HYP-ADR-CONT-M15-001",
    "state": "killed",
    "parent_candidate": None,
    "feature_family": "m15_adr_extreme_continuation",
    "lane": "unlimited_goal_price_m15",
    "setup_type": "ADR100% extreme continuation opposite ADRExhaust; D1 EMA50; Mon-Thu",
    "symbol": "USDJPY",
    "timeframe": "M15",
    "window": "2021.01.01-2025.12.31",
    "model": 0,
    "source_provenance": "Owner MT autonomy 2026-07-14; opposite ADRExhaust S681",
    "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_ADR_CONT_M15_001_PREREG.md",
    "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_ADR_CONT_M15_001_READOUT.md",
    "exact_overrides": "",
    "variant_tag": "HYP_ADR_CONT_M15_001_MODEL0",
    "source_path": "03. EA Developer/EA_M15ADRCont/EA_M15ADRCont.mq5",
    "run_ids": ["20260714_031538"],
    "metrics": {"trades": 146, "pf": 0.887, "net": -510.65, "tpw": 0.56, "max_dd_pct": 6.95},
    "validation": {
        "cost_stress": "tester current only",
        "report_sha256": "63FF90F1195EBEBBAF6658C9E844D63A2485FA4A6BD132E6D99887CECA2C6F64",
        "receipt_sha256": "A5B506CB9B327AAC8C950BB416AF263A0B96E64C0FD221ACABE868C8B0C26D2E",
    },
    "verdict": "kill",
    "reason": "PF 0.887 and tpw~0.56; kill floor; do not mine ADR/extreme/day",
    "updated_at": "2026-07-14",
}
with reg.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False) + "\n")
print("appended", row["state"], row["hypothesis_id"])
