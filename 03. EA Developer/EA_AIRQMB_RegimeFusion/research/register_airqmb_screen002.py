from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SOURCE_V1 = "A0622C7BCB22F1DBAABD707B1159679283D6B2C1AD0CFE642C5301E4573B1A81"
SOURCE_V2 = "07D94050A8142353E6E0DD491334CED5631E3B0EF12011B8119AD92A28208B52"
PREREG_V1 = "90A5FAE4F1B4ED70847527D033F34E975FE8552812533D1A8C311DE508895C57"
PREREG_V2 = "06B87976EFEF6C7ACBEB9F09084915649E7ABD83BE79A2D00EDB6FDDD570B634"
UPDATED = "2026-08-05T18:31:00Z"

CELLS = [
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

ACCEPTANCE = {
    "min_profit_factor": 1.3,
    "min_trades_per_week": 2.0,
    "max_trades_per_week": 5.0,
    "max_drawdown_pct": 8.0,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1.0,
    "max_monte_carlo_p95_dd_pct": 8.0,
}


def base_fields(symbol: str, hypothesis_id: str, model: int, source_hash: str, prereg: str, prereg_hash: str) -> dict:
    return {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": hypothesis_id,
        "ea_name": "EA_AIRQMB_RegimeFusion",
        "parent_candidate": None,
        "feature_family": "aird-mbb-qqe-semantic-regime-fusion",
        "lane": f"AIRQMB-{symbol}-M5-{'MODEL4-SCREEN' if model == 4 else 'BASELINE'}",
        "symbol": symbol,
        "timeframe": "M5",
        "window": {"from": "2023.01.02", "to": "2024.12.31"},
        "model": model,
        "source_provenance": (
            "Owner-directed three-indicator semantic ensemble; outcome-blind engine "
            "successor after an aborted no-report runtime smoke."
        ),
        "source_path": "03. EA Developer/EA_AIRQMB_RegimeFusion/EA_AIRQMB_RegimeFusion.mq5",
        "source_hash": source_hash,
        "prereg_path": prereg,
        "prereg_sha256": prereg_hash,
        "evidence_contract_kind": "economic",
        "acceptance_contract": ACCEPTANCE,
        "updated_at_utc": UPDATED,
        "run_ids": [],
    }


def main() -> None:
    lines = [line for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    latest: dict[str, dict] = {}
    for line in lines:
        row = json.loads(line)
        latest[row["hypothesis_id"]] = row

    screen_ids = [f"HYP-AIRQMB-{symbol}-M5-SCREEN-002" for symbol, _ in CELLS]
    duplicates = [hypothesis_id for hypothesis_id in screen_ids if hypothesis_id in latest]
    if duplicates:
        raise SystemExit(f"refusing duplicate screen registration: {duplicates}")

    appended: list[dict] = []
    for symbol, magic in CELLS:
        old_id = f"HYP-AIRQMB-{symbol}-M5-BASE-001"
        if old_id not in latest or latest[old_id].get("state") != "probe":
            raise SystemExit(f"unexpected BASE-001 state for {old_id}")
        parked = base_fields(
            symbol,
            old_id,
            0,
            SOURCE_V1,
            "03. EA Developer/EA_AIRQMB_RegimeFusion/research/HYP-AIRQMB-MULTI9-M5-001_FROZEN_PREREG.md",
            PREREG_V1,
        )
        parked.update(
            {
                "state": "parked",
                "exact_overrides": latest[old_id]["exact_overrides"],
                "verdict": "SUPERSEDED_NO_ECONOMIC_OUTCOME",
                "reason": (
                    "EURUSD engineering smoke was stopped before report after excessive runtime; "
                    "no outcome was read. All nine BASE-001 cells are superseded together by the "
                    "outcome-blind per-bar engine and Model-4 screen protocol."
                ),
                "metrics": {
                    "mt5_launches": 1 if symbol == "EURUSD" else 0,
                    "reports_generated": 0,
                    "performance_outcome_reads": 0,
                    "economic_trials_consumed": 0,
                },
                "validation": {
                    "model0_authorized": False,
                    "optimization_authorized": False,
                    "validation_access_authorized": False,
                    "holdout_access_authorized": False,
                    "economic_valid": False,
                    "promotion_eligible": False,
                    "successor": f"HYP-AIRQMB-{symbol}-M5-SCREEN-002",
                    "abort_receipt_sha256": "50E26B2DBD96D4384269C7BA42C9A9EDF73AA1ADF9CA4BCF141D5F8EA96D9C64",
                },
            }
        )
        appended.append(parked)

        new_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-002"
        screen = base_fields(
            symbol,
            new_id,
            4,
            SOURCE_V2,
            "03. EA Developer/EA_AIRQMB_RegimeFusion/research/HYP-AIRQMB-MULTI9-M5-SCREEN-002_FROZEN_PREREG.md",
            PREREG_V2,
        )
        screen.update(
            {
                "state": "probe",
                "parent_candidate": old_id,
                "exact_overrides": (
                    f"InpExpectedSymbol={symbol};InpHypothesisId={new_id};InpMagic={magic};"
                    "InpResearchAutoMode=true;InpVariantTag=SCREEN002_MODEL4"
                ),
                "verdict": "PREREGISTERED_MODEL4_SCREEN_NOT_RUN",
                "reason": (
                    "Model-4 runtime/cadence/provisional-PF screen authorized. It cannot establish "
                    "economic validity; Model-0 confirmation, validation and holdout remain locked."
                ),
                "metrics": {},
                "validation": {
                    "compile_status": "PASS_0_ERRORS_0_WARNINGS",
                    "nonrepaint_status": "PASS",
                    "model4_screen_authorized": True,
                    "model0_authorized": False,
                    "optimization_authorized": False,
                    "validation_access_authorized": False,
                    "holdout_access_authorized": False,
                    "economic_valid": False,
                    "promotion_eligible": False,
                    "screen_min_profit_factor": 1.10,
                    "screen_min_trades_per_week": 1.5,
                    "screen_max_trades_per_week": 6.0,
                    "logic_matrix_sha256": "845B2A309FDFB5E6B9D1F5A7A897AE92AEA9E21A7200B2F5E478D0274E98A47B",
                    "nonrepaint_audit_sha256": "E610712609537A45CCDF271D8FF09BA23233D1D868AE1612B8DAF88323FF6D2F",
                },
            }
        )
        appended.append(screen)

    with REGISTRY.open("a", encoding="utf-8", newline="\n") as handle:
        for row in appended:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")
    print(f"parked 9 BASE-001 rows and registered 9 SCREEN-002 rows")


if __name__ == "__main__":
    main()
