#!/usr/bin/env python3
"""Append thick-edge wave registry rows + contract receipts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"

REGS = [
    {
        "hypothesis_id": "HYP-H4-NR7-BREAK-001",
        "state": "preregistered",
        "parent_candidate": "HARD_EMPTY_CONTINUES_thick_edge",
        "feature_family": "h4_nr7_compression_break",
        "lane": "thick_expectancy_rebuild_20260714",
        "setup_type": "H4 NR7 then next closed-H4 breakout; RR=3.0; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "H4",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner thick-edge wave; independent of VolExp/Keltner/H4-struct",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_H4_NR7_BREAK_001_PREREG.md",
        "readout_path": None,
        "exact_overrides": "",
        "variant_tag": "HYP_H4_NR7_001",
        "source_path": "03. EA Developer/EA_H4NR7Break/EA_H4NR7Break.mq5",
        "run_ids": [],
        "metrics": None,
        "validation": {
            "cost_stress": "tester current + x1.5/x2 if HIT",
            "dedup": "readouts/20260714_THICK_EDGE_WAVE_DEDUP_CLEARANCE.md",
        },
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "updated_at": "2026-07-14",
        "fam_dir": "h4_nr7_break",
    },
    {
        "hypothesis_id": "HYP-D1-TREND-H4-PB-001",
        "state": "preregistered",
        "parent_candidate": "HARD_EMPTY_CONTINUES_thick_edge",
        "feature_family": "d1_ema_trend_h4_pb_reclaim",
        "lane": "thick_expectancy_rebuild_20260714",
        "setup_type": "D1 EMA50 bias + H4 EMA20 PB reclaim; RR=3.0; multi-day; Mon-Thu",
        "symbol": "USDJPY",
        "timeframe": "H4",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner thick-edge wave; independent of H1-ATR-mom / EMA-stretch fade / ITSM",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_D1_TREND_H4_PB_001_PREREG.md",
        "readout_path": None,
        "exact_overrides": "",
        "variant_tag": "HYP_D1_H4_PB_001",
        "source_path": "03. EA Developer/EA_D1TrendH4PB/EA_D1TrendH4PB.mq5",
        "run_ids": [],
        "metrics": None,
        "validation": {
            "cost_stress": "tester current + x1.5/x2 if HIT",
            "dedup": "readouts/20260714_THICK_EDGE_WAVE_DEDUP_CLEARANCE.md",
        },
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "updated_at": "2026-07-14",
        "fam_dir": "d1_trend_h4_pb",
    },
    {
        "hypothesis_id": "HYP-WEEKLY-HL-BREAK-H4-001",
        "state": "preregistered",
        "parent_candidate": "HARD_EMPTY_CONTINUES_thick_edge",
        "feature_family": "weekly_hl_h4_close_break",
        "lane": "thick_expectancy_rebuild_20260714",
        "setup_type": "Prior W1 HL H4 close break; RR=3.0; Mon-Thu; multi-symbol stub if sparse",
        "symbol": "USDJPY",
        "timeframe": "H4",
        "window": "2021.01.01-2025.12.31",
        "model": 0,
        "source_provenance": "Owner thick-edge wave; not PDH/PDL; not LNY DualWin",
        "prereg_path": "03. EA Developer/EA_SonicR/research/preregs/20260714_H_WEEKLY_HL_BREAK_H4_001_PREREG.md",
        "readout_path": None,
        "exact_overrides": "",
        "variant_tag": "HYP_WEEKLY_HL_001",
        "source_path": "03. EA Developer/EA_WeeklyHLBreak_H4/EA_WeeklyHLBreak_H4.mq5",
        "run_ids": [],
        "metrics": None,
        "validation": {
            "cost_stress": "tester current + x1.5/x2 if HIT",
            "dedup": "readouts/20260714_THICK_EDGE_WAVE_DEDUP_CLEARANCE.md",
        },
        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
        "updated_at": "2026-07-14",
        "fam_dir": "weekly_hl_break_h4",
    },
]


def main() -> None:
    existing = REG.read_text(encoding="utf-8") if REG.exists() else ""
    with REG.open("a", encoding="utf-8") as f:
        for r in REGS:
            if r["hypothesis_id"] in existing and '"state":"preregistered"' in existing:
                # allow re-append only if not already present as this wave
                if f'"hypothesis_id":"{r["hypothesis_id"]}"' in existing and "thick_expectancy_rebuild_20260714" in existing:
                    print("SKIP already present", r["hypothesis_id"])
                    continue
            fam = r.pop("fam_dir")
            cdir = (
                ROOT
                / "03. EA Developer"
                / "EA_SonicR"
                / "research"
                / "preflight"
                / fam
                / "contracts"
            )
            cdir.mkdir(parents=True, exist_ok=True)
            receipt = {
                "schema_version": "sonic_contract_receipt.v1",
                "hypothesis_id": r["hypothesis_id"],
                "prereg_path": r["prereg_path"],
                "source_path": r["source_path"],
                "dedup": "03. EA Developer/EA_SonicR/research/readouts/20260714_THICK_EDGE_WAVE_DEDUP_CLEARANCE.md",
                "frozen_at": "2026-07-14",
                "model": 0,
                "symbol": "USDJPY",
                "timeframe": "H4",
                "window": "2021.01.01-2025.12.31",
                "deposit": 100000,
                "tp_ratio": 3.0,
                "risk_pct": 0.5,
            }
            body = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
            sha = hashlib.sha256(body).hexdigest().upper()
            receipt["receipt_sha256"] = sha
            (cdir / f"20260714_{r['hypothesis_id']}_CONTRACT_RECEIPT.json").write_text(
                json.dumps(receipt, indent=2), encoding="utf-8"
            )
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                **r,
                "contract_receipt_sha256": sha,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(r["hypothesis_id"], sha)
    print("done")


if __name__ == "__main__":
    main()
