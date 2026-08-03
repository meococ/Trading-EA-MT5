#!/usr/bin/env python3
"""Close HYP-LOMX-DESIGN-M5-002 after its sole outcome-blind P0 run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path


HYPOTHESIS_ID = "HYP-LOMX-DESIGN-M5-002"
RESULT_REL = (
    "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/evidence/"
    "HYP-LOMX-DESIGN-M5-002/P0_DESIGN_001/stage0_result.json"
)
RESULT_SHA256 = "8193E68D4EC240B696CDB91884C95976F3B47ECFFF740D5416BE2BEB4D2EF1DB"
READOUT_REL = (
    "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/"
    "HYP-LOMX-DESIGN-M5-002_STAGE0_READOUT.md"
)
READOUT_SHA256 = "5AB8DA24B68821412AB14FF1EF4DC6CF33B981CA9CABC9570D6A7F5F51868CDA"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    validator = registry.with_name("validate_candidate_registry.py")
    result_path = root / RESULT_REL
    readout_path = root / READOUT_REL
    if sha256_file(result_path) != RESULT_SHA256:
        raise ValueError("stage0 result hash mismatch")
    if sha256_file(readout_path) != READOUT_SHA256:
        raise ValueError("stage0 readout hash mismatch")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("performance_outcome_read") or result.get("economics_executed"):
        raise ValueError("stage0 result violated the outcome-blind contract")
    if result.get("full_plan_p0_pass") is not False:
        raise ValueError("closeout expects the frozen full-plan P0 failure")

    lines = registry.read_text(encoding="utf-8-sig").splitlines()
    matches = [
        json.loads(line)
        for line in lines
        if json.loads(line).get("hypothesis_id") == HYPOTHESIS_ID
    ]
    if not matches or matches[-1].get("state") != "probe":
        raise ValueError("latest LOMX design row must be probe")
    row = deepcopy(matches[-1])
    row["state"] = "parked"
    row["verdict"] = (
        "PARK_FULL_DUAL_ENGINE_CADENCE_OVERFLOW_ATOMIC_CELLS_SURVIVE_NO_OUTCOME"
    )
    row["reason"] = (
        "All four atomic symbol-engine cells passed outcome-blind density and "
        "geometry gates, but the simultaneous stream produced 8.5705 candidates/week "
        "on EURUSD and 8.7260 on XAUUSD versus the frozen 2-5 band, with 6/12 "
        "opposing same-bar collisions. The exact combined plan is parked before PnL."
    )
    row["updated_at_utc"] = "2026-08-02T17:16:51Z"
    row["run_ids"] = ["P0_DESIGN_001"]
    row["metrics"] = {
        **row.get("metrics", {}),
        "stage0_runs": 1,
        "valid_stage0_runs": 1,
        "atomic_cells_passed": 4,
        "full_plan_p0_pass": False,
        "eurusd_sweep_candidates": 1949,
        "eurusd_sweep_candidates_per_week": 4.153120243531203,
        "eurusd_breakout_candidates": 2117,
        "eurusd_breakout_candidates_per_week": 4.511111111111111,
        "xauusd_sweep_candidates": 2085,
        "xauusd_sweep_candidates_per_week": 4.442922374429224,
        "xauusd_breakout_candidates": 2072,
        "xauusd_breakout_candidates_per_week": 4.415220700152207,
        "eurusd_combined_candidates_per_week": 8.570471841704718,
        "xauusd_combined_candidates_per_week": 8.726027397260275,
        "mt5_launches": 0,
        "economic_trials_consumed": 0,
        "performance_outcome_reads": 0,
    }
    row["validation"] = {
        **row.get("validation", {}),
        "probe_status": "PARK_FULL_PLAN_COMBINED_CADENCE_FAIL_NO_OUTCOME",
        "source_build_authorized": False,
        "model0_authorized": False,
        "performance_metrics_authorized": False,
        "economic_validity_authorized": False,
        "economics_authorized": False,
        "optimization_authorized": False,
        "promotion_eligible": False,
        "validation_access_authorized": False,
        "holdout_access_authorized": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "atomic_successor_ideas_authorized": True,
        "stage0_result_path": RESULT_REL,
        "stage0_result_sha256": RESULT_SHA256,
        "candidate_csv_path": result["candidate_csv"],
        "candidate_csv_sha256": result["candidate_csv_sha256"],
        "scanner_path": result["scanner_path"],
        "scanner_sha256": result["scanner_sha256"],
        "readout_path": READOUT_REL,
        "readout_sha256": READOUT_SHA256,
        "failure_radius": (
            "Exact simultaneous two-arm stream, fixed thresholds, symbols, UTC "
            "session and 2016-2024 design window. Atomic cells remain separate ideas."
        ),
    }
    compact = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
    payload = ("\n".join(lines + [compact]) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".jsonl", delete=False) as handle:
        staged = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        subprocess.run(
            ["python", str(validator), "--registry", str(staged)], cwd=root, check=True
        )
        if args.apply:
            temporary = registry.with_name(f".{registry.name}.{os.getpid()}.tmp")
            temporary.write_bytes(payload)
            temporary.replace(registry)
            subprocess.run(["python", str(validator)], cwd=root, check=True)
    finally:
        staged.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "status": "APPLIED" if args.apply else "STAGED_PASS",
                "hypothesis_id": HYPOTHESIS_ID,
                "state": "parked",
                "verdict": row["verdict"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
