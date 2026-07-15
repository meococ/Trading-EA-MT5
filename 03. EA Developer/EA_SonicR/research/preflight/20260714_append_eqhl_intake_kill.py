#!/usr/bin/env python3
"""Append EQHL intake-kill + optionally later IB probe kill/park rows."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"

rows = [
    {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": "HYP-H1-EQHL-SWEEP-RECLAIM-001",
        "state": "killed",
        "parent_candidate": "post_pin_threebar_stub",
        "feature_family": "h1_eqhl_liquidity_sweep_reclaim",
        "lane": "post_pin_thick_edge_20260714",
        "setup_type": "EQH/EQL sweep then closed-bar reclaim (proposed)",
        "symbol": "USDJPY",
        "timeframe": "H1",
        "window": "n/a",
        "model": "intake_dedup_only",
        "source_provenance": "De-dup fail-closed vs AsianSweep reclaim + H1SwingFailure/SFP",
        "prereg_path": None,
        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_H1_EQHL_SWEEP_RECLAIM_DEDUP_INTAKE_KILL.md",
        "exact_overrides": "",
        "variant_tag": "HYP_H1_EQHL_SWEEP_RECLAIM_001_INTAKE",
        "source_path": None,
        "run_ids": [],
        "metrics": None,
        "validation": {
            "dedup": "readouts/20260714_H1_EQHL_SWEEP_RECLAIM_DEDUP_INTAKE_KILL.md",
            "status": "KILL_AT_INTAKE_DUPLICATE",
        },
        "cost_grade": "n/a",
        "verdict": "KILL_AT_INTAKE_DUPLICATE",
        "reason": "Same sweep-reclaim/SFP archetype as killed ASR + H1SwingFailure; level-constructor swap is densify",
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
