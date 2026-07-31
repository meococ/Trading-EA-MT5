#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "03. EA Developer" / "EA_VRAS_VolatilityNormalizedStop"
RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_VolatilityNormalizedStop" / "20260722_225229"
OUT = PKG / "research" / "HYP-VRAS-EURUSD-M5-006_DELIVERY_PACKET.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def bind(role: str, path: Path) -> dict:
    return {"role": role, "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size, "sha256": sha(path)}


def main() -> int:
    lifecycle = next((RUN / "analysis" / "logs").glob("*_LifecycleTrades_*.csv"))
    runmeta = next((RUN / "analysis" / "logs").glob("*_RunMeta_*.json"))
    paths = {
        "preregistration": PKG / "research" / "HYP-VRAS-EURUSD-M5-006_FROZEN_PREREG.md",
        "logic_matrix": PKG / "research" / "LOGIC_TO_CODE_MATRIX.md",
        "source": PKG / "EA_VRAS_VolatilityNormalizedStop.mq5",
        "compiled_binary": PKG / "EA_VRAS_VolatilityNormalizedStop.ex5",
        "compile_log": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-006_COMPILE_RECEIPT.txt",
        "test_receipt": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-006_TEST_RECEIPT.json",
        "nonrepaint_audit": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-006_NONREPAINT_AUDIT.json",
        "run_manifest": RUN / "run_manifest.json",
        "tester_report": RUN / "report.html",
        "lifecycle_trades": lifecycle,
        "run_meta": runmeta,
        "log_triage": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-006_LOG_TRIAGE.json",
        "casebook_manifest": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-006_DELIVERY_ANATOMY" / "cases_manifest.json",
        "decision_casebook_manifest": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-006_DECISION_ASOF_INDICATORS" / "cases_manifest.json",
        "readout": PKG / "research" / "HYP-VRAS-EURUSD-M5-006_READOUT.md",
        "economic_analysis": PKG / "research" / "HYP-VRAS-EURUSD-M5-006_FORENSIC_ANALYSIS.md",
        "matched_pair_metrics": PKG / "research" / "HYP-VRAS-EURUSD-M5-006_READOUT.json",
        "indicator_anatomy_manifest": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-006_CHARTS" / "cases_manifest.json",
    }
    statuses = {name: "COMPLETE" for name in (
        "economics", "cost_stress", "cadence", "time_stability", "session_breakdown",
        "direction_breakdown", "execution_quality", "funnel", "winning_trade_causes",
        "losing_trade_causes", "logic_conflicts", "limitations")}
    statuses["regime_breakdown"] = "INSUFFICIENT_EXPLAINED"
    payload = {
        "schema_version": "alphafactory_ea_delivery_packet.v1",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-006",
        "ea_name": "EA_VRAS_VolatilityNormalizedStop",
        "delivery_class": "economic_run",
        "completion_claim": True,
        "verdict": "KILLED",
        "bindings": [bind(role, path) for role, path in paths.items()],
        "logic_contract": {"requirements_total": 11, "requirements_mapped_to_code": 11,
            "requirements_tested": 11, "closed_bar_decisions": True,
            "unresolved_material_ambiguities": 0},
        "engineering_contract": {"tests_passed": 7, "tests_failed": 0,
            "compile_errors": 0, "compile_warnings": 0, "nonrepaint_status": "PASS"},
        "run_contract": {"run_id": "20260722_225229", "model": 0, "trades": 158,
            "report_lifecycle_reconciled": True, "lifecycle_open_rows": 158,
            "lifecycle_final_rows": 158, "unresolved_log_errors": 0},
        "analysis_contract": {"statuses": statuses,
            "exceptions": {"regime_breakdown": "HYP006 emits no independent regime label; no post-hoc regime proxy is allowed to rescue the failed matched pair."}},
        "chart_contract": {"minimum_each": 2, "higher_timeframe_context": True,
            "higher_timeframe": "M15", "entry_candle_centered": True,
            "post_entry_bars_visible": True, "outcome_region_labeled": True,
            "sample_basis": "wins_and_losses", "entry_sl_tp_exit_visible": True,
            "available_winners": 57, "available_losers": 101,
            "rendered_winners": 2, "rendered_losers": 2,
            "decision_asof_separate": True, "decision_outcome_hidden": True,
            "decision_net_r_hidden": True, "decision_active_indicators_visible": True,
            "decision_indicator_provenance": "diagnostic_recompute_nonparity_labeled"},
        "anti_overfit_contract": {"plan_frozen_pre_outcome": True,
            "one_change_one_run": True, "posthoc_rule_change_authorized": False},
        "limitations": [
            "Cost, commission and slippage provenance remains UNVERIFIED_DIAGNOSTIC_ONLY.",
            "Both arms hit the account DD entry latch in Q1 2019, so no later-window trades exist.",
            "Decision indicators are non-parity diagnostic recomputations from hash-bound broker M1 bars.",
            "Generic datalog summary does not ingest lifecycle-v3; exact direct reconciliation is used.",
            "No Monte Carlo, WFA or sensitivity run is justified after base and relative gate failure."
        ]
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUT} sha256={sha(OUT)} bindings={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
