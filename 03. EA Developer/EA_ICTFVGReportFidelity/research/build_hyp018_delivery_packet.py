#!/usr/bin/env python3
"""Build the hash-bound zero-trade terminal delivery packet for HYP-018."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"D:\Trading EA MT5")
HYP = "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018"
PKG = ROOT / "03. EA Developer" / "EA_ICTFVGReportFidelity"
RESEARCH = PKG / "research"
EVIDENCE = RESEARCH / "evidence"
RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_ICTFVGReportFidelity" / "20260719_235851"
CHARTS = ROOT / "02. AlphaFactory" / "runtime" / "ict_fvg_hyp018_collection_receipt" / "rejection_charts"
OUT = EVIDENCE / f"{HYP}_DELIVERY_PACKET.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def binding(role: str, path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing delivery artifact: {path}")
    return {"role": role, "path": relative(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def one(pattern: str) -> Path:
    matches = list((RUN / "logs").glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {pattern}, found {len(matches)}")
    return matches[0]


def build() -> dict:
    paths = {
        "preregistration": RESEARCH / f"{HYP}_COLLECTION_PLAN.md",
        "logic_matrix": RESEARCH / f"{HYP}_LOGIC_TO_CODE_MATRIX.md",
        "source": RESEARCH / "source_snapshots" / f"EA_ICTFVGReportFidelity_{HYP}.mq5",
        "compiled_binary": RUN / "snapshot" / "build" / "EA_ICTFVGReportFidelity.ex5",
        "compile_log": EVIDENCE / "HYP018_COMPILE_SUMMARY_UTF8.log",
        "test_receipt": EVIDENCE / "20260719_HYP018_DELIVERY_TEST_RECEIPT.json",
        "nonrepaint_audit": EVIDENCE / "20260719_NONREPAINT_AUDIT_V20",
        "run_manifest": RUN / "run_manifest.json",
        "tester_report": RUN / "report.html",
        "lifecycle_trades": one("*_LifecycleTrades_*.csv"),
        "run_meta": one("*_RunMeta_*.json"),
        "log_triage": EVIDENCE / "HYP018_LOG_TRIAGE.json",
        "funnel_analysis": EVIDENCE / f"{HYP}_COLLECTION_RESULT.json",
        "casebook_manifest": CHARTS / "cases_manifest.json",
        "readout": RESEARCH / f"{HYP}_READOUT.md",
        "tick_initiation": one("*_TickInitiation_*.csv"),
        "human_context": one("*_HumanContext_*.csv"),
        "source_binary_receipt": EVIDENCE / "20260719_SOURCE_BINARY_RECEIPT_V25.json",
        "raw_compile_log": RESEARCH / "source_snapshots" / f"EA_ICTFVGReportFidelity_{HYP}.compile.log",
        "collection_analyzer": RESEARCH / "analyze_hyp018_tick_collection.py",
        "delivery_trial_log": EVIDENCE / "HYP018_DELIVERY_TRIAL_LOG.jsonl",
    }
    return {
        "schema_version": "alphafactory_ea_delivery_packet.v1",
        "created_at_utc": "2026-07-19T17:15:00Z",
        "hypothesis_id": HYP,
        "ea_name": "EA_ICTFVGReportFidelity",
        "delivery_class": "zero_trade_terminal",
        "completion_claim": True,
        "verdict": "KILLED",
        "bindings": [binding(role, path) for role, path in paths.items()],
        "logic_contract": {
            "requirements_total": 6,
            "requirements_mapped_to_code": 6,
            "requirements_tested": 6,
            "closed_bar_decisions": True,
            "unresolved_material_ambiguities": 0,
        },
        "engineering_contract": {
            "tests_passed": 65,
            "tests_failed": 0,
            "compile_errors": 0,
            "compile_warnings": 0,
            "nonrepaint_status": "PASS",
        },
        "run_contract": {
            "run_id": "20260719_235851",
            "model": 0,
            "trades": 0,
            "report_lifecycle_reconciled": True,
            "lifecycle_open_rows": 0,
            "lifecycle_final_rows": 0,
            "unresolved_log_errors": 0,
        },
        "analysis_contract": {
            "statuses": {
                "economics": "NOT_APPLICABLE_ZERO_TRADES",
                "cost_stress": "NOT_APPLICABLE_ZERO_TRADES",
                "cadence": "COMPLETE",
                "time_stability": "COMPLETE",
                "session_breakdown": "COMPLETE",
                "direction_breakdown": "COMPLETE",
                "regime_breakdown": "COMPLETE",
                "execution_quality": "COMPLETE",
                "funnel": "COMPLETE",
                "winning_trade_causes": "NOT_APPLICABLE_ZERO_TRADES",
                "losing_trade_causes": "NOT_APPLICABLE_ZERO_TRADES",
                "logic_conflicts": "COMPLETE",
                "limitations": "COMPLETE",
            },
            "exceptions": {
                "economics": "The frozen collection was required to open zero trades, so economics are undefined.",
                "cost_stress": "No order or trade exists and therefore cost stress has no defined economic quantity.",
                "winning_trade_causes": "No trade outcome was created or authorized in the collection contract.",
                "losing_trade_causes": "No trade outcome was created or authorized in the collection contract.",
            },
        },
        "chart_contract": {
            "sample_basis": "rejections",
            "available_winners": 0,
            "available_losers": 0,
            "rendered_winners": 0,
            "rendered_losers": 0,
            "available_rejections": 966,
            "rendered_rejections": 2,
            "minimum_each": 2,
            "entry_sl_tp_exit_visible": False,
            "higher_timeframe_context": True,
            "higher_timeframe": "H1",
            "entry_candle_centered": True,
            "post_entry_bars_visible": True,
            "outcome_region_labeled": True,
        },
        "anti_overfit_contract": {
            "plan_frozen_pre_outcome": True,
            "one_change_one_run": True,
            "posthoc_rule_change_authorized": False,
        },
        "limitations": [
            "Full-bar quote-mid tick sign is a broker-feed proxy and failed the frozen materiality gate.",
            "The zero-trade collection cannot establish economic edge or cost robustness.",
            "The two rejection charts are terminal anatomy only and cannot seed a same-sample rule.",
            "Historical same-broker cost provenance remains unresolved independently.",
        ],
    }


def main() -> int:
    payload = build()
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packet": relative(OUT), "sha256": sha(OUT), "bindings": len(payload["bindings"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
