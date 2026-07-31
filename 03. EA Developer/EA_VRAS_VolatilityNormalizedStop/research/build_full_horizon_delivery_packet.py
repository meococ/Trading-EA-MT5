#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "03. EA Developer" / "EA_VRAS_VolatilityNormalizedStop"
CONTROL = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_VolatilityNormalizedStop" / "20260722_233324"
CHALLENGER = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_VolatilityNormalizedStop" / "20260722_233420"
OUT = PKG / "research" / "HYP-VRAS-EURUSD-M5-008_DELIVERY_PACKET.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def bind(role: str, path: Path) -> dict:
    return {
        "role": role,
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha(path),
    }


def one(run: Path, pattern: str) -> Path:
    return next((run / "analysis" / "logs").glob(pattern))


def main() -> int:
    paths = {
        "preregistration": PKG / "research" / "HYP-VRAS-EURUSD-M5-008_FULL_HORIZON_DIAGNOSTIC_PLAN.md",
        "logic_matrix": PKG / "research" / "LOGIC_TO_CODE_MATRIX.md",
        "source": CHALLENGER / "snapshot" / "source" / "EA_VRAS_VolatilityNormalizedStop.mq5",
        "compiled_binary": CHALLENGER / "snapshot" / "build" / "EA_VRAS_VolatilityNormalizedStop.ex5",
        "compile_log": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-008_COMPILE_RECEIPT.txt",
        "test_receipt": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-008_TEST_RECEIPT.json",
        "nonrepaint_audit": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-008_NONREPAINT_AUDIT.json",
        "run_manifest": CHALLENGER / "run_manifest.json",
        "tester_report": CHALLENGER / "report.html",
        "lifecycle_trades": one(CHALLENGER, "*_LifecycleTrades_*.csv"),
        "run_meta": one(CHALLENGER, "*_RunMeta_*.json"),
        "log_triage": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-008_LOG_TRIAGE.json",
        "casebook_manifest": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-008_DELIVERY_ANATOMY" / "cases_manifest.json",
        "decision_casebook_manifest": PKG / "research" / "evidence" / "HYP-VRAS-EURUSD-M5-008_DECISION_ASOF_INDICATORS" / "cases_manifest.json",
        "readout": PKG / "research" / "HYP-VRAS-EURUSD-M5-008_READOUT.md",
        "economic_analysis": PKG / "research" / "HYP-VRAS-EURUSD-M5-008_FORENSIC_ANALYSIS.md",
        "matched_pair_metrics": PKG / "research" / "HYP-VRAS-EURUSD-M5-008_READOUT.json",
        "control_run_manifest": CONTROL / "run_manifest.json",
        "control_tester_report": CONTROL / "report.html",
        "control_lifecycle_trades": one(CONTROL, "*_LifecycleTrades_*.csv"),
        "control_run_meta": one(CONTROL, "*_RunMeta_*.json"),
        "control_log_window": ROOT / "02. AlphaFactory" / "runtime" / "log_indexes" / "95ef51636cf7" / "20260722.log.window_150175_30.json",
        "challenger_log_window": ROOT / "02. AlphaFactory" / "runtime" / "log_indexes" / "95ef51636cf7" / "20260722.log.window_181790_30.json",
        "control_equity_audit": CONTROL / "analysis" / "equity_audit.json",
        "challenger_equity_audit": CHALLENGER / "analysis" / "equity_audit.json",
        "control_overnight_exposure": CONTROL / "analysis" / "overnight_exposure.json",
        "challenger_overnight_exposure": CHALLENGER / "analysis" / "overnight_exposure.json",
    }
    statuses = {name: "COMPLETE" for name in (
        "economics", "cost_stress", "cadence", "time_stability", "session_breakdown",
        "direction_breakdown", "regime_breakdown", "execution_quality", "funnel",
        "winning_trade_causes", "losing_trade_causes", "logic_conflicts", "limitations",
    )}
    payload = {
        "schema_version": "alphafactory_ea_delivery_packet.v1",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-008",
        "ea_name": "EA_VRAS_VolatilityNormalizedStop",
        "delivery_class": "economic_run",
        "completion_claim": True,
        "verdict": "KILLED",
        "bindings": [bind(role, path) for role, path in paths.items()],
        "logic_contract": {
            "requirements_total": 14,
            "requirements_mapped_to_code": 14,
            "requirements_tested": 14,
            "closed_bar_decisions": True,
            "unresolved_material_ambiguities": 0,
        },
        "engineering_contract": {
            "tests_passed": 11,
            "tests_failed": 0,
            "compile_errors": 0,
            "compile_warnings": 0,
            "nonrepaint_status": "PASS",
        },
        "run_contract": {
            "run_id": "20260722_233420",
            "model": 0,
            "trades": 3611,
            "report_lifecycle_reconciled": True,
            "lifecycle_open_rows": 3611,
            "lifecycle_final_rows": 3611,
            "unresolved_log_errors": 0,
        },
        "analysis_contract": {"statuses": statuses, "exceptions": {}},
        "chart_contract": {
            "minimum_each": 2,
            "higher_timeframe_context": True,
            "higher_timeframe": "M15",
            "entry_candle_centered": True,
            "post_entry_bars_visible": True,
            "outcome_region_labeled": True,
            "sample_basis": "wins_and_losses",
            "entry_sl_tp_exit_visible": True,
            "available_winners": 1524,
            "available_losers": 2087,
            "rendered_winners": 2,
            "rendered_losers": 2,
            "decision_asof_separate": True,
            "decision_outcome_hidden": True,
            "decision_net_r_hidden": True,
            "decision_active_indicators_visible": True,
            "decision_indicator_provenance": "diagnostic_recompute_nonparity_labeled",
        },
        "anti_overfit_contract": {
            "plan_frozen_pre_outcome": True,
            "one_change_one_run": True,
            "posthoc_rule_change_authorized": False,
        },
        "limitations": [
            "HYP008 is diagnostic-only: the EA account-DD entry halt is disabled only in Strategy Tester.",
            "Tester deposit/risk scaling preserves approximate initial USD 50 cash risk but is not a live sizing recommendation.",
            "Cost, commission, slippage and news provenance remains UNVERIFIED_DIAGNOSTIC_ONLY.",
            "Decision indicators are labeled non-parity diagnostic recomputations from hash-bound broker bars.",
            "The 24 completed-M5-bar time exit pauses over market closure and permits weekend-gap tails.",
            "Generic validate-full WFA, Monte Carlo and robustness outputs were auto-generated outside the frozen plan and are excluded from this verdict.",
            "No R:R, stop, ATR, session, year, direction or weekend-rule rescue is authorized under HYP008.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {OUT} sha256={sha(OUT)} bindings={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
