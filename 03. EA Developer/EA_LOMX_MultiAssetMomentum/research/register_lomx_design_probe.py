#!/usr/bin/env python3
"""Register the frozen outcome-blind LOMX design probe atomically."""

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
PLAN_REL = (
    "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/"
    "HYP-LOMX-DESIGN-M5-002_PROBE_PLAN.md"
)
EXPECTED_PLAN_SHA256 = "FB44311871144290B231DA3AFC083C89B4D950768D7FA1D5F4E61C695B8CD09E"
UPDATED_AT_IDEA = "2026-08-02T17:10:54Z"
UPDATED_AT_PROBE = "2026-08-02T17:10:55Z"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def compact(row: dict[str, object]) -> str:
    return json.dumps(row, separators=(",", ":"), ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[3]
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
    validator = registry.with_name("validate_candidate_registry.py")
    plan = root / PLAN_REL
    if sha256_file(plan) != EXPECTED_PLAN_SHA256:
        raise ValueError("frozen LOMX design probe plan hash mismatch")

    lines = registry.read_text(encoding="utf-8-sig").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    if any(row.get("hypothesis_id") == HYPOTHESIS_ID for row in rows):
        raise ValueError(f"{HYPOTHESIS_ID} already exists in the registry")

    acceptance = {
        "min_profit_factor": 1.3,
        "min_trades_per_week": 2.0,
        "max_trades_per_week": 5.0,
        "max_drawdown_pct": 8.0,
        "min_cost_pf_x1_5": 1.25,
        "min_cost_pf_x2": 1.0,
        "max_monte_carlo_p95_dd_pct": 8.0,
    }
    base: dict[str, object] = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": "EA_LOMX_MultiAssetMomentum",
        "state": "idea",
        "parent_candidate": (
            "Owner implementation_plan.md plus invalid unregistered "
            "HYP-LOMX-MULTI-M5-001 engineering draft; zero economic exposure"
        ),
        "feature_family": (
            "outcome-blind-xauusd-eurusd-m5-asian-range-sweep-reclaim-"
            "and-bar-range-compression-breakout-density-matrix"
        ),
        "lane": "LOMX-XAUUSD-EURUSD-M5-ATOMIC-DESIGN-P0",
        "symbol": "MULTI_XAUUSD_EURUSD",
        "timeframe": "M5",
        "window": {"from": "2016.01.04", "to": "2024.12.31"},
        "model": 0,
        "source_provenance": (
            "Owner build-first plan reviewed against terminal LOMX M1, PO3, "
            "ASRS and ECRS evidence. The two arms are separated and the generic "
            "compression arm is explicitly not the frozen T2 Volman grammar. "
            "FivePercent foundation M5 hashes are frozen in the plan."
        ),
        "source_path": None,
        "source_hash": None,
        "prereg_path": PLAN_REL,
        "prereg_sha256": EXPECTED_PLAN_SHA256,
        "exact_overrides": (
            "OutcomeBlindOnly;Symbols=EURUSD|XAUUSD;M5;2016-2024;"
            "SessionUTC=07:00-16:00;AsianUTC=00:00-06:00_72bars;"
            "ArmA=Sweep0.30ATR_Reclaim_VolZ1.50_SL0.20ATR_TP1Mid_TP2OppositeMin1.50R;"
            "ArmB=Range2LT0.70xPrior50_BoxBars2to16_Break0.20ATR_VolGTMean20_"
            "SLBox0.10ATR_TP2R;Collision=SweepPriority;NoPnLNoFutureNoGridNoRescue"
        ),
        "evidence_contract_kind": "economic",
        "acceptance_contract": acceptance,
        "verdict": "OPEN_OWNER_BUILD_FIRST_OUTCOME_BLIND_ATOMIC_DESIGN_PROBE",
        "reason": (
            "A cheap four-cell density/geometry probe is required before any "
            "economic hypothesis or MT5 Model 0. Strong adverse adjacent-family "
            "priors are declared rather than treated as a blanket veto."
        ),
        "updated_at_utc": UPDATED_AT_IDEA,
        "run_ids": [],
        "metrics": {
            "stage0_runs": 0,
            "mt5_launches": 0,
            "economic_trials_consumed": 0,
            "performance_outcome_reads": 0,
            "atomic_cells": 4,
        },
        "validation": {
            "dedup_status": "LEGAL_OUTCOME_BLIND_DESIGN_ONLY_STRONG_ADVERSE_PRIOR",
            "probe_status": "FROZEN_PLAN_IMPLEMENTATION_PENDING",
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
            "cost_status": "UNVERIFIED_NOT_REQUIRED_FOR_OUTCOME_BLIND_DENSITY",
            "outcome_blind": True,
        },
    }
    probe = deepcopy(base)
    probe["state"] = "probe"
    probe["verdict"] = "FROZEN_REAL_OUTCOME_BLIND_DENSITY_PROBE_AUTHORIZED"
    probe["reason"] = (
        "Authorize one deterministic scanner implementation, synthetic tests and "
        "one four-cell run on the exact frozen M5 datasets. No trade outcome or "
        "MT5 economic execution is authorized."
    )
    probe["updated_at_utc"] = UPDATED_AT_PROBE
    probe_validation = dict(probe["validation"])
    probe_validation["probe_status"] = "AUTHORIZED_ONE_DETERMINISTIC_OUTCOME_BLIND_RUN"
    probe["validation"] = probe_validation

    payload = ("\n".join(lines + [compact(base), compact(probe)]) + "\n").encode("utf-8")
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
                "states": ["idea", "probe"],
                "plan_sha256": EXPECTED_PLAN_SHA256,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
