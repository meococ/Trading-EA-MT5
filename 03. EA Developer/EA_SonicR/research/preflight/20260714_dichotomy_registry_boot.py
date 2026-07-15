#!/usr/bin/env python3
"""Append dichotomy-break preregistered rows before offline probes."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"


def row(obj: dict) -> dict:
    base = {
        "record_type": "candidate",
        "schema_version": 1,
        "readout_path": None,
        "run_ids": [],
        "metrics": None,
        "updated_at": "2026-07-14",
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "lane": "dichotomy_break_20260714",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner dichotomy-break panel; GPT waived; offline-first",
    }
    base.update(obj)
    return base


def main() -> None:
    rows = [
        row(
            {
                "hypothesis_id": "HYP-RR2-EXIT-BE1R-M15PATH-001",
                "state": "preregistered",
                "parent_candidate": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
                "feature_family": "rr2_exit_be1r_m15path",
                "setup_type": "BE@1R exit architecture on frozen RR2; not densify",
                "symbol": "USDJPY",
                "timeframe": "M15",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_RR2_EXIT_BE1R_M15PATH_001_PREREG.md",
                "exact_overrides": "DONOR=20260714_194548;BE_AT_R=1.0;KEEP_ORIGINAL_TP=1",
                "variant_tag": "HYP_RR2_EXIT_BE1R_M15PATH_001",
                "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
                "validation": {
                    "status": "PREREG_FROZEN_AWAITING_OFFLINE_PROBE",
                    "dedup": "readouts/20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md",
                    "panel": "readouts/20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md",
                },
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-RR2-USJP-YIELD-ZGATE-001",
                "state": "preregistered",
                "parent_candidate": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
                "feature_family": "rr2_usjp_yield_z_allow_gate",
                "setup_type": "US-JP 10Y |z| allow-gate on frozen RR2; not bond signal",
                "symbol": "USDJPY",
                "timeframe": "M15",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_RR2_USJP_YIELD_ZGATE_001_PREREG.md",
                "exact_overrides": "DONOR=20260714_194548;YIELD_Z_ABS=0.75;LOOKBACK=60",
                "variant_tag": "HYP_RR2_USJP_YIELD_ZGATE_001",
                "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
                "validation": {
                    "status": "PREREG_FROZEN_AWAITING_OFFLINE_PROBE",
                    "dedup": "readouts/20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md",
                    "panel": "readouts/20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md",
                },
            }
        ),
        row(
            {
                "hypothesis_id": "HYP-BOOK-CORRCAP-RR2-SPARK-001",
                "state": "preregistered",
                "parent_candidate": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
                "feature_family": "book_corr_cap_rr2_spark",
                "setup_type": "max concurrent=1 CorrCap RR2+Spark; not Phase-0 ceremony",
                "symbol": "USDJPY",
                "timeframe": "M15",
                "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_BOOK_CORRCAP_RR2_SPARK_001_PREREG.md",
                "exact_overrides": "RR2=20260714_194548;SPARK=20260714_193358;MAX_CONCURRENT=1",
                "variant_tag": "HYP_BOOK_CORRCAP_RR2_SPARK_001",
                "source_path": "03. EA Developer/EA_SilverBullet/EA_SilverBullet_v2.mq5",
                "validation": {
                    "status": "PREREG_FROZEN_AWAITING_OFFLINE_PROBE",
                    "dedup": "readouts/20260714_DICHOTOMY_BREAK_DEDUP_CLEARANCE.md",
                    "panel": "readouts/20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md",
                    "phase0": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
                },
            }
        ),
    ]
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"appended": [r["hypothesis_id"] for r in rows]}, indent=2))


if __name__ == "__main__":
    main()
