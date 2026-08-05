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
SOURCE_V5 = "AB4D63AD66984636F1E8D6D6291B91280220D85E30E52ECB04F1ACF7F40FC4B0"
SOURCE_V6 = "16A6284D85B354E9F774AFD36F2C194609AC1E339A3891EB1E72B0807E3DBB8C"
PREREG_V6 = "72C21A99236EEEE8A13FD074571A6E6E3714FEDD160C0504297B865AE8293F11"
SNAPSHOT_V5 = (
    "03. EA Developer/EA_AIRQMB_RegimeFusion/research/source_snapshots/"
    "EA_AIRQMB_RegimeFusion_AB4D63AD66984636.mq5"
)


def main() -> None:
    lines = [line for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    latest: dict[str, dict] = {}
    for line in lines:
        row = json.loads(line)
        latest[row["hypothesis_id"]] = row
    appended: list[dict] = []

    for symbol, magic in SYMBOLS:
        screen4_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-004"
        screen4 = latest[screen4_id]
        if screen4.get("state") != "parked" or "source_snapshot_path" in screen4.get("validation", {}):
            raise SystemExit(f"unexpected SCREEN-004 terminal state: {screen4_id}")
        screen4_snapshot = deepcopy(screen4)
        screen4_snapshot["validation"]["source_snapshot_path"] = SNAPSHOT_V5
        screen4_snapshot["validation"]["source_snapshot_sha256"] = SOURCE_V5
        appended.append(screen4_snapshot)

        old_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-005"
        prior = latest[old_id]
        if prior.get("state") != "probe":
            raise SystemExit(f"unexpected SCREEN-005 state: {old_id}")

        parked = deepcopy(prior)
        parked["state"] = "parked"
        parked["verdict"] = "ENGINEERING_INVALID_ORDERCHECK_GATE_NO_ECONOMIC_OUTCOME"
        parked["reason"] = (
            "EURUSD produced a 100%-real-tick report and healthy signal funnel, but all 4,067 "
            "admissible entries were blocked by treating successful OrderCheck retcode 0 as failure. "
            "No OrderSend occurred, so all nine cells are engineering-invalid, not economically tested."
        )
        parked["updated_at_utc"] = "2026-08-05T19:16:00Z"
        parked["run_ids"] = ["20260806_021144"] if symbol == "EURUSD" else []
        parked["metrics"] = {
            "mt5_launches": 1 if symbol == "EURUSD" else 0,
            "reports_generated": 1 if symbol == "EURUSD" else 0,
            "performance_outcome_reads": 0,
            "economic_trials_consumed": 0,
            "history_quality_pct": 100.0 if symbol == "EURUSD" else None,
            "closed_bars": 148937 if symbol == "EURUSD" else 0,
            "raw_signals": 4067 if symbol == "EURUSD" else 0,
            "ordercheck_rejects": 4067 if symbol == "EURUSD" else 0,
            "entries_opened": 0,
        }
        parked["validation"].update({
            "engineering_valid": False,
            "model4_screen_authorized": False,
            "optimization_authorized": False,
            "economic_valid": False,
            "promotion_eligible": False,
            "successor": f"HYP-AIRQMB-{symbol}-M5-SCREEN-006",
            "source_snapshot_path": SNAPSHOT_V5,
            "source_snapshot_sha256": SOURCE_V5,
            "failure_packet_sha256": "E65826B07ED355F7A8BC47337F67A2EDCB1900BC33F8DB6D167D01B79B6F97F5",
        })
        appended.append(parked)

        new_id = f"HYP-AIRQMB-{symbol}-M5-SCREEN-006"
        screen = {
            "record_type": "hypothesis_state",
            "schema_version": "alphafactory_candidate_registry.v1",
            "hypothesis_id": new_id,
            "ea_name": "EA_AIRQMB_RegimeFusion",
            "state": "probe",
            "parent_candidate": old_id,
            "feature_family": "aird-mbb-qqe-semantic-regime-fusion-ordercheck-repair",
            "lane": f"AIRQMB-{symbol}-M5-ORDERCHECK-MODEL4-SCREEN",
            "symbol": symbol,
            "timeframe": "M5",
            "window": {"from": "2023.01.02", "to": "2024.12.31"},
            "model": 4,
            "source_provenance": (
                "Engineering successor after a zero-entry report: OrderCheck true/retcode-0 now proceeds "
                "to OrderSend; indicator and strategy decision mathematics unchanged."
            ),
            "source_path": "03. EA Developer/EA_AIRQMB_RegimeFusion/EA_AIRQMB_RegimeFusion.mq5",
            "source_hash": SOURCE_V6,
            "prereg_path": (
                "03. EA Developer/EA_AIRQMB_RegimeFusion/research/"
                "HYP-AIRQMB-MULTI9-M5-SCREEN-006_FROZEN_PREREG.md"
            ),
            "prereg_sha256": PREREG_V6,
            "exact_overrides": (
                f"InpExpectedSymbol={symbol};InpHypothesisId={new_id};InpMagic={magic};"
                "InpResearchAutoMode=true;InpVariantTag=SCREEN006_ORDERCHECK_MODEL4"
            ),
            "evidence_contract_kind": "economic",
            "acceptance_contract": prior["acceptance_contract"],
            "verdict": "PREREGISTERED_ORDERCHECK_MODEL4_SCREEN_NOT_RUN",
            "reason": (
                "OrderCheck-repaired Model-4 screen authorized. Confirmation, "
                "optimization, validation, holdout and promotion remain locked."
            ),
            "updated_at_utc": "2026-08-05T19:16:00Z",
            "run_ids": [],
            "metrics": {},
            "validation": {
                "compile_status": "PASS_0_ERRORS_0_WARNINGS",
                "nonrepaint_status": "PASS",
                "indicator_runtime_smoke_required": False,
                "order_execution_smoke_required": True,
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
                "nonrepaint_audit_sha256": "9BC4D3151403D9152166C68279355F05660990E34D2DF95477B3D3000DB40329",
                "indicator_source_sha256": {
                    "AIRD": "D010798CDEDAEF77CB4F8F8C4BE51A8B35F17EBFC298EBB64A0B329060746759",
                    "MBB": "2E96AEFE68F1F094FF9FA2CE23802CB94D5592F8526B29A30BE393E1340544B3",
                    "QQE": "22456C83C73D2070F52D83BBCE7D5DC1982CD987F8BE807E10482703982CAF9A",
                },
            },
        }
        appended.append(screen)

    with REGISTRY.open("a", encoding="utf-8", newline="\n") as handle:
        for row in appended:
            handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=True) + "\n")
    print("snapshotted 9 SCREEN-004 rows, parked 9 SCREEN-005 rows and registered 9 SCREEN-006 rows")


if __name__ == "__main__":
    main()
