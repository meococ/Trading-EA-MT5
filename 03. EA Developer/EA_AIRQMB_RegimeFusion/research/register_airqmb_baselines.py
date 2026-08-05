from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SYMBOLS = [
    ("EURUSD", 5686101),
    ("USDJPY", 5686102),
    ("GBPUSD", 5686103),
    ("USDCHF", 5686104),
    ("USDCAD", 5686105),
    ("AUDUSD", 5686106),
    ("NZDUSD", 5686107),
    ("XAUUSD", 5686108),
    ("BTCUSD", 5686109),
]


def make_row(symbol: str, magic: int) -> dict:
    hypothesis_id = f"HYP-AIRQMB-{symbol}-M5-BASE-001"
    return {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": hypothesis_id,
        "ea_name": "EA_AIRQMB_RegimeFusion",
        "state": "probe",
        "parent_candidate": None,
        "feature_family": "aird-mbb-qqe-semantic-regime-fusion",
        "lane": f"AIRQMB-{symbol}-M5-BASELINE",
        "symbol": symbol,
        "timeframe": "M5",
        "window": {"from": "2023.01.02", "to": "2024.12.31"},
        "model": 0,
        "source_provenance": (
            "Owner-directed new three-indicator ensemble frozen before first MT5 "
            "performance launch; not a rescue of prior killed identities."
        ),
        "source_path": "03. EA Developer/EA_AIRQMB_RegimeFusion/EA_AIRQMB_RegimeFusion.mq5",
        "source_hash": "A0622C7BCB22F1DBAABD707B1159679283D6B2C1AD0CFE642C5301E4573B1A81",
        "prereg_path": (
            "03. EA Developer/EA_AIRQMB_RegimeFusion/research/"
            "HYP-AIRQMB-MULTI9-M5-001_FROZEN_PREREG.md"
        ),
        "prereg_sha256": "90A5FAE4F1B4ED70847527D033F34E975FE8552812533D1A8C311DE508895C57",
        "exact_overrides": (
            f"InpExpectedSymbol={symbol};InpHypothesisId={hypothesis_id};"
            f"InpMagic={magic};InpResearchAutoMode=true;InpVariantTag=BASELINE_FROZEN"
        ),
        "evidence_contract_kind": "economic",
        "acceptance_contract": {
            "min_profit_factor": 1.3,
            "min_trades_per_week": 2.0,
            "max_trades_per_week": 5.0,
            "max_drawdown_pct": 8.0,
            "min_cost_pf_x1_5": 1.25,
            "min_cost_pf_x2": 1.0,
            "max_monte_carlo_p95_dd_pct": 8.0,
        },
        "verdict": "PREREGISTERED_BASELINE_NOT_RUN",
        "reason": (
            "Independent Model-0 training baseline authorized; validation, holdout "
            "and optimization remain locked until baseline gates pass."
        ),
        "updated_at_utc": "2026-08-05T18:00:33Z",
        "run_ids": [],
        "metrics": {},
        "validation": {
            "compile_status": "PASS_0_ERRORS_0_WARNINGS",
            "nonrepaint_status": "PASS",
            "model0_authorized": True,
            "optimization_authorized": False,
            "validation_access_authorized": False,
            "holdout_access_authorized": False,
            "economic_valid": False,
            "promotion_eligible": False,
            "logic_matrix_sha256": "25DC3D5FF5E4E1C379979CB9C27203D6CE8E42EA81B3883521ED4B27769A0E66",
            "nonrepaint_audit_sha256": "B4CEC7BC47F0734F6BEFEBD2EDEB47CE5D6DA4A88A372F24F40EA1B151FCB363",
        },
    }


def main() -> None:
    existing = {
        json.loads(line)["hypothesis_id"]
        for line in REGISTRY.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    rows = [make_row(symbol, magic) for symbol, magic in SYMBOLS]
    duplicates = [row["hypothesis_id"] for row in rows if row["hypothesis_id"] in existing]
    if duplicates:
        raise SystemExit(f"refusing duplicate registry append: {duplicates}")
    with REGISTRY.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")
    print(f"registered {len(rows)} AIRQMB baseline hypotheses")


if __name__ == "__main__":
    main()
