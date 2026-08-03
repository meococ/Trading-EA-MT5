#!/usr/bin/env python3
"""Append the screened HYP-LASR-XAUUSD-M5-001 registry row once."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HYPOTHESIS_ID = "HYP-LASR-XAUUSD-M5-001"
EA_NAME = "EA_LOMX_MultiAssetMomentum"
OVERRIDES = (
    "InpResearchAutoMode=true;InpEnableTelemetry=true;"
    "InpHypothesisId=HYP-LASR-XAUUSD-M5-001;"
    "InpVariantTag=LASR_XAU_SWEEP_MODEL0;InpEngineMode=0;"
    "InpMagic=5603101;InpRiskPercent=0.25;InpMaxDailyLossPct=3.5;"
    "InpMaxAccountDrawdownPct=8.0;InpMaxTradesPerDay=3;"
    "InpMaxSpreadToRisk=0.15;InpDeviationPoints=20;InpATRPeriod=14;"
    "InpSweepEpsilonMult=0.30;InpSweepStopAtrMult=0.20;"
    "InpSweepMinTp2R=1.50;InpVolumeLookback=20;InpVolumeThreshold=1.50;"
    "InpAsianStartMinutesUtc=0;InpAsianEndMinutesUtc=360;"
    "InpTradeStartMinutesUtc=420;InpTradeEndMinutesUtc=960;"
    "InpDailyFlattenMinutesUtc=1200;InpFridayFlattenMinutesUtc=1200;"
    "InpSweepScaleOutFraction=0.50;InpMaxHoldBars=96;"
    "InpLotConsistencyMinFills=10;InpLotConsistencyLookbackFills=10;"
    "InpLotConsistencyMinFactor=0.50;InpLotConsistencyMaxFactor=1.50"
)
ACCEPTANCE = {
    "min_profit_factor": 1.3,
    "min_trades_per_week": 2.0,
    "max_trades_per_week": 5.0,
    "max_drawdown_pct": 8.0,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1.0,
    "max_monte_carlo_p95_dd_pct": 8.0,
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def repo_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    package = root / "03. EA Developer" / EA_NAME
    source = package / f"{EA_NAME}.mq5"
    prereg = package / "research" / "HYP-LASR-XAUUSD-M5-001_FROZEN_PREREG.md"
    cost_manifest = package / "research" / "preflight" / HYPOTHESIS_ID / "cost_source_manifest.json"
    nonrepaint = package / "research" / "evidence" / HYPOTHESIS_ID / "STATIC_AUDIT" / "NONREPAINT_AUDIT_RERUN.json"
    compile_log = package / f"{EA_NAME}.log"
    ex5 = package / f"{EA_NAME}.ex5"
    registry = root / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"

    for required in (source, prereg, cost_manifest, nonrepaint, compile_log, ex5, registry):
        if not required.is_file():
            raise FileNotFoundError(required)

    refresh = "--refresh" in sys.argv[1:]
    existing = [
        json.loads(raw)
        for raw in registry.read_text(encoding="utf-8-sig").splitlines()
        if raw.strip()
        and json.loads(raw).get("hypothesis_id") == HYPOTHESIS_ID
    ]
    if existing and not refresh:
        print(json.dumps({"status": "already_registered", "latest_state": existing[-1].get("state")}))
        return 0

    cost = load_json(cost_manifest)
    audit = load_json(nonrepaint)
    if cost.get("evidence_tier") != "RESEARCH_PROXY" or cost.get("promotion_eligible") is not False:
        raise ValueError("cost manifest is not a non-promotable research proxy")
    if audit.get("status") != "PASS":
        raise ValueError("non-repaint audit is not PASS")

    row: dict[str, Any] = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": EA_NAME,
        "state": "screened",
        "parent_candidate": "HYP-LOMX-DESIGN-M5-002" if not existing else HYPOTHESIS_ID,
        "feature_family": "xauusd-m5-asian-range-sweep-reclaim-research-cost-proxy",
        "lane": "LASR-XAUUSD-M5-SWEEP-HYP001-RESEARCH-PROXY",
        "symbol": "XAUUSD",
        "timeframe": "M5",
        "window": {"from": "2018.01.02", "to": "2022.12.30"},
        "model": 0,
        "source_provenance": (
            "Fresh atomic successor to parked HYP-LOMX-DESIGN-M5-002. Only the "
            "XAUUSD Asian-range sweep-reclaim sleeve is authorized; the generic "
            "compression breakout and simultaneous dual-engine stream are excluded. "
            "No HYP-LASR Model-0 outcome existed when this row was frozen."
        ),
        "source_path": repo_path(source, root),
        "source_hash": sha256_file(source),
        "prereg_path": repo_path(prereg, root),
        "prereg_sha256": sha256_file(prereg),
        "exact_overrides": OVERRIDES,
        "evidence_contract_kind": "economic",
        "acceptance_contract": ACCEPTANCE,
        "verdict": (
            "SCREENED_RESEARCH_PROXY_ENGINEERING_HASH_REFRESH_MODEL0_ELIGIBLE_NON_PROMOTABLE"
            if existing
            else "SCREENED_RESEARCH_PROXY_PRIMARY_MODEL0_ELIGIBLE_NON_PROMOTABLE"
        ),
        "reason": (
            "Outcome-blind P0 found the XAUUSD sweep atomic cell at 4.4429 "
            "candidates/week while the combined plan failed cadence. Research "
            "proxy cost evidence covers 2018.01.02-2022.12.30 only; raw tick "
            "spread acquisition for 2016-2024 failed closed. Exactly one primary "
            "Model-0 falsification is eligible; economic-valid, promotion, paper "
            "and live remain forbidden under every result."
            if not existing
            else "Refresh-only screened row after final compile/non-repaint rerun; no "
            "MT5 Model-0 launch, outcome read, strategy change, parameter change or "
            "trial consumption occurred between screened rows."
        ),
        "updated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "run_ids": [],
        "metrics": {
            "inherited_xauusd_sweep_candidates": 2085,
            "inherited_xauusd_sweep_candidates_per_week": 4.442922374429224,
            "compile_errors": 0,
            "compile_warnings": 0,
            "ex5_bytes": ex5.stat().st_size,
            "historical_spread_sample_count": cost["historical_spread_provenance"]["coverage"]["sample_count"],
            "historical_spread_coverage_ratio": cost["historical_spread_provenance"]["coverage"]["coverage_ratio"],
            "commission_proxy_lifecycles": cost["commission_provenance"]["sample_count"],
            "commission_proxy_usd_per_lot_max": cost["commission_provenance"]["value"],
            "quote_proxy_samples": cost["slippage_provenance"]["sample_count"],
            "quote_proxy_p90_roundturn_pips": cost["slippage_provenance"]["p90_roundturn"],
            "mt5_launches": 0,
            "economic_trials_consumed": 0,
            "economics_executed": False,
        },
        "validation": {
            "probe_status": "SCREENED_RESEARCH_PROXY_PRIMARY_MODEL0_ELIGIBLE",
            "source_build_authorized": False,
            "model0_authorized": True,
            "research_falsification_authorized": True,
            "performance_metrics_authorized": True,
            "economic_validity_authorized": False,
            "economics_authorized": False,
            "optimization_authorized": False,
            "promotion_eligible": False,
            "validation_access_authorized": False,
            "holdout_access_authorized": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
            "market_edge_claim_authorized": False,
            "cost_status": "VERIFIED_RESEARCH_PROXY_NON_PROMOTION",
            "cost_source_manifest_path": repo_path(cost_manifest, root),
            "cost_source_manifest_sha256": sha256_file(cost_manifest),
            "compile_log_path": repo_path(compile_log, root),
            "compile_log_sha256": sha256_file(compile_log),
            "ex5_sha256": sha256_file(ex5),
            "nonrepaint_status": "PASS",
            "nonrepaint_audit_path": repo_path(nonrepaint, root),
            "nonrepaint_audit_sha256": sha256_file(nonrepaint),
            "identity_fingerprint_basis": {
                "broker": cost["broker"],
                "server": cost["server"],
                "currency": cost["account_currency"],
                "digits": cost["symbol_geometry"]["digits"],
                "point": cost["symbol_geometry"]["point"],
                "pip_size": cost["symbol_geometry"]["pip_size"],
            },
            "broker_fingerprint": cost["broker_fingerprint"],
            "server_fingerprint": cost["server_fingerprint"],
            "account_fingerprint": cost["account_fingerprint"],
            "data_fingerprint": cost["data_fingerprint"],
            "promotion_blocker": (
                "Commission is Strategy Tester simulation and quote-latency evidence "
                "has no observed fill; promotion-grade commission/slippage are absent."
            ),
        },
    }
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
    print(json.dumps({"status": "registered", "hypothesis_id": HYPOTHESIS_ID, "state": "screened"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
