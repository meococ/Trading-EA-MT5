# -*- coding: utf-8 -*-
from pathlib import Path
import json

reg = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\CANDIDATE_REGISTRY.jsonl")
rows = [
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H1-LOWVOL-DONCHIAN-MR-001",
        "state": "killed",
        "parent_candidate": None,
        "feature_family": "h1_lowvol_donchian_mr",
        "lane": "unlimited_goal_h1_structure",
        "setup_type": "Low ATR fade Donchian20 to mid; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "H1",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner exclusive-tester reopen 2026-07-14; magic on disk 880960",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H1_LOWVOL_DONCHIAN_MR_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_HYP_H1_LOWVOL_DONCHIAN_MR_001_READOUT.md",
        "exact_overrides": "",
        "variant_tag": "HYP_H1_LOWVOL_DONCHIAN_MR_001_MODEL0",
        "source_path": "03. EA Developer/EA_H1LowVolDonchianMR/EA_H1LowVolDonchianMR.mq5",
        "run_ids": ["20260714_221055", "20260714_220749"],
        "metrics": {"trades": 1, "pf": 999.99, "net": 45.36, "tpw": 0.004, "max_dd_pct": 0.0},
        "validation": {
            "cost_stress": "tester current only",
            "report_sha256": "D7FA0D5F016EA39B65590653A428A61772B8E26B0197B0CB1B5478DAFC699A0A",
            "receipt_sha256": "FF99F5037AD6AE78C3C8CCFDBF65E7A8F07B045812AD58B57B6E8D5A9B4914DD",
            "ticks_approx": 6483501,
            "note": "ticks << H1 ATR-mom reference; twin rerun identical",
        },
        "verdict": "kill",
        "reason": "N=1 and tpw~0.004; kill floor; do not mine ATR/Donchian",
        "updated_at": "2026-07-14",
    },
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-PORTFOLIO-SB-SPARK-RUNNER-001",
        "state": "preregistered",
        "parent_candidate": "HYP-PORTFOLIO-COMPOSE-001",
        "feature_family": "portfolio_sb_spark_runner",
        "lane": "fx_portfolio_silverbullet_phase0",
        "setup_type": "Exact SB A1 + Spark Asian dual-sleeve runner; offline probe only this turn",
        "symbol": "USDJPY",
        "timeframe": "M15",
        "window": "2021.01.01-2025.12.31",
        "model": "offline_probe_then_runner_build",
        "source_provenance": "Owner refine mandate; offline compose NEAR_GOAL proxy",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_PORTFOLIO_SB_SPARK_RUNNER_001_PREREG.md",
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_OFFLINE_SB_SPARK_COMPOSE_PROBE_V1.md",
        "exact_overrides": "SLEEVE_A:InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseWeekendFlat=1 | SLEEVE_B:defaults",
        "variant_tag": "HYP_PORTFOLIO_SB_SPARK_RUNNER_001_PROBE",
        "run_ids": ["20260714_002505", "20260714_002614"],
        "metrics": {"pooled_pf": 1.339, "pooled_tpw": 3.24, "pooled_n": 845},
        "validation": {
            "phase0_contamination": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
            "cost": "UNVERIFIED_TESTER_DEFAULT",
            "blocker": "NO_SPARK_MODULE_IN_EA_PORTFOLIO_SCAFFOLD",
        },
        "verdict": "probe_pass_awaiting_runner_build",
        "reason": "Offline NEAR_GOAL proxy; Model0 deferred until Spark sleeve scaffold exists",
        "updated_at": "2026-07-14",
    },
]
with reg.open("a", encoding="utf-8") as f:
    for row in rows:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print("appended", row["hypothesis_id"], row["state"])
