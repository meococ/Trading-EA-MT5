from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
SYMBOLS = [
    ("EURUSD", 5686101), ("USDJPY", 5686102), ("GBPUSD", 5686103),
    ("USDCHF", 5686104), ("USDCAD", 5686105), ("AUDUSD", 5686106),
    ("NZDUSD", 5686107), ("XAUUSD", 5686108), ("BTCUSD", 5686109),
]
SOURCE_V2 = "07D94050A8142353E6E0DD491334CED5631E3B0EF12011B8119AD92A28208B52"
SOURCE_V3 = "B8AA382C4586646D8C932765B34E6DA10F97C90925D67BC19BFC7FFF4ED623A8"
PREREG_V2 = "06B87976EFEF6C7ACBEB9F09084915649E7ABD83BE79A2D00EDB6FDDD570B634"
PREREG_V3 = "D59ED62BA4EBC2512AF11F0476E5473922C13B67A9A1B50ABDEE2757A9AB9D3C"
SNAPSHOT_V2 = (
    "03. EA Developer/EA_AIRQMB_RegimeFusion/research/source_snapshots/"
    "EA_AIRQMB_RegimeFusion_07D94050A8142353.mq5"
)


def main() -> None:
    lines = [line for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    latest: dict[str, dict] = {}
    for line in lines:
        row = json.loads(line)
        latest[row["hypothesis_id"]] = row
    appended: list[dict] = []
    for symbol, magic in SYMBOLS:
        old_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-002"
        prior = latest[old_id]
        if prior.get("state") != "probe":
            raise SystemExit(f"unexpected SCREEN-002 state: {old_id}")
        parked = deepcopy(prior)
        parked["state"] = "parked"
        parked["verdict"] = "SUPERSEDED_HEADLESS_NO_ECONOMIC_OUTCOME"
        parked["reason"] = (
            "EURUSD Model-4 smoke was stopped before report after static profiling found "
            "avoidable AIRD/MBB/QQE display-object overhead; no outcome was read. All nine "
            "cells are superseded together by the outcome-blind headless iCustom source."
        )
        parked["updated_at_utc"] = "2026-08-05T18:53:00Z"
        parked["metrics"] = {
            "mt5_launches": 1 if symbol == "EURUSD" else 0,
            "reports_generated": 0,
            "performance_outcome_reads": 0,
            "economic_trials_consumed": 0,
        }
        parked["validation"].update({
            "model4_screen_authorized": False,
            "optimization_authorized": False,
            "economic_valid": False,
            "promotion_eligible": False,
            "successor": f"HYP-AIRQMB-{symbol}-M5-SCREEN-003",
            "source_snapshot_path": SNAPSHOT_V2,
            "source_snapshot_sha256": SOURCE_V2,
            "abort_receipt_sha256": "1F8025134FE51035DC5C829EB4AAAA8F5C0B9FFF4EB755A0435A758FA845725B",
        })
        appended.append(parked)

        new_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-003"
        screen = {
            "record_type": "hypothesis_state",
            "schema_version": "alphafactory_candidate_registry.v1",
            "hypothesis_id": new_id,
            "ea_name": "EA_AIRQMB_RegimeFusion",
            "state": "probe",
            "parent_candidate": old_id,
            "feature_family": "aird-mbb-qqe-semantic-regime-fusion-headless",
            "lane": f"AIRQMB-{symbol}-M5-HEADLESS-MODEL4-SCREEN",
            "symbol": symbol,
            "timeframe": "M5",
            "window": {"from": "2023.01.02", "to": "2024.12.31"},
            "model": 4,
            "source_provenance": (
                "Outcome-blind headless integration successor; all indicator mathematical defaults "
                "and public buffer equations unchanged, display objects and alerts disabled."
            ),
            "source_path": "03. EA Developer/EA_AIRQMB_RegimeFusion/EA_AIRQMB_RegimeFusion.mq5",
            "source_hash": SOURCE_V3,
            "prereg_path": (
                "03. EA Developer/EA_AIRQMB_RegimeFusion/research/"
                "HYP-AIRQMB-MULTI9-M5-SCREEN-003_FROZEN_PREREG.md"
            ),
            "prereg_sha256": PREREG_V3,
            "exact_overrides": (
                f"InpExpectedSymbol={symbol};InpHypothesisId={new_id};InpMagic={magic};"
                "InpResearchAutoMode=true;InpVariantTag=SCREEN003_HEADLESS_MODEL4"
            ),
            "evidence_contract_kind": "economic",
            "acceptance_contract": prior["acceptance_contract"],
            "verdict": "PREREGISTERED_HEADLESS_MODEL4_SCREEN_NOT_RUN",
            "reason": (
                "Headless Model-4 runtime/cadence/provisional-PF screen authorized. Model-0, "
                "optimization, validation, holdout and promotion remain locked."
            ),
            "updated_at_utc": "2026-08-05T18:53:00Z",
            "run_ids": [],
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
                "nonrepaint_audit_sha256": "D739E3A2CCB825F0D2D6ACAD53FD4C68912DC72F56DB4DC6F3A14949BA7A47E5",
            },
        }
        appended.append(screen)
    with REGISTRY.open("a", encoding="utf-8", newline="\n") as handle:
        for row in appended:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")
    print("parked 9 SCREEN-002 rows and registered 9 SCREEN-003 rows")


if __name__ == "__main__":
    main()
