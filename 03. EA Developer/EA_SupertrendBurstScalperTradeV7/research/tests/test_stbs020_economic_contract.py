from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
V6 = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV6/EA_SupertrendBurstScalperTradeV6.mq5"
PACKAGE = Path(__file__).resolve().parents[2]
V7 = PACKAGE / "EA_SupertrendBurstScalperTradeV7.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST = PACKAGE / "research/HYP-STBS-XAUUSD-M15-020_RESEARCH_COST_SOURCE_MANIFEST.json"
PREREG = PACKAGE / "research/HYP-STBS-XAUUSD-M15-020_MODEL0_BASELINE_PREREG.md"


def source() -> str:
    return V7.read_text(encoding="utf-8")


def test_v7_is_exact_identity_only_v6_revision():
    text = source()
    normalized = (text
        .replace('#property version   "7.00"', '#property version   "6.00"')
        .replace('#property description "H1 Supertrend flip economic baseline with account-safe margin and lifecycle-v3 evidence."', '#property description "H1 Supertrend flip trade baseline with account-safe margin and lifecycle-v3 evidence."')
        .replace('HYP-STBS-XAUUSD-M15-020', 'HYP-STBS-XAUUSD-M15-019')
        .replace('STBS_H1_FLIP_M15_BURST_TRADE_V7_ACCOUNT_SAFE', 'STBS_H1_FLIP_M15_BURST_TRADE_V6_ACCOUNT_SAFE')
        .replace('5604120', '5604119')
        .replace('EA_SupertrendBurstScalperTradeV7', 'EA_SupertrendBurstScalperTradeV6'))
    assert normalized == V6.read_text(encoding="utf-8")


def test_trade_identity_and_lifecycle_are_frozen():
    text = source()
    assert 'input bool   InpAuditOnly           = false;' in text
    assert 'input bool   InpEnableTelemetry     = true;' in text
    assert 'InpHypothesisId!="HYP-STBS-XAUUSD-M15-020"' in text
    assert 'InpVariantTag!="STBS_H1_FLIP_M15_BURST_TRADE_V7_ACCOUNT_SAFE"' in text
    assert 'InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604120' in text
    assert json.loads(CONTRACT.read_text(encoding="utf-8"))["telemetry_profile"] == "lifecycle-v3"


def test_frozen_signal_risk_lifecycle_and_design_contract_survives():
    text = source()
    for needle in (
        "const int ST_ATR_PERIOD          = 10;", "const double ST_FACTOR           = 3.0;",
        "const int M15_ATR_PERIOD         = 14;", "input double InpRiskPercent         = 0.25;",
        "input double InpStopAtrMult         = 1.00;", "input double InpTargetRR            = 1.50;",
        "input int    InpMaxHoldBars         = 8;", "DESIGN_START_TIME", "DESIGN_END_TIME",
        "InpMoneyHeadroomReserveFactor   = 0.20", "InpMaxNewPositionMarginPct     = 5.00",
        "bool ReconcileLifecycleHistory()", "g_lifecycle_positions_opened!=g_lifecycle_positions_final_closed",
    ):
        assert needle in text
    assert text.count("OrderSend(request,result)") == 3


def test_cost_manifest_has_exact_research_proxy_provenance_schema():
    cost = json.loads(COST.read_text(encoding="utf-8"))
    assert cost["evidence_tier"] == "RESEARCH_PROXY"
    assert cost["promotion_eligible"] is False
    assert cost["account_fingerprint"] == "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"
    assert cost["data_fingerprint"] == "B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25"
    assert cost["run_meta_contract"]["hypothesis_id"] == "HYP-STBS-XAUUSD-M15-020"
    assert cost["run_meta_contract"]["magic"] == 5604120
    assert cost["historical_spread_provenance"]["symbol"] == "XAUUSD"
    assert cost["historical_spread_provenance"]["coverage"]["coverage_ratio"] == 1.0
    assert cost["commission_provenance"]["source_kind"] == "strategy_tester_simulation"
    assert cost["commission_provenance"]["value"] == 4.4
    assert cost["slippage_provenance"]["sample_count"] == 31176
    assert cost["slippage_provenance"]["p90_roundturn"] == 80.00000000001819
    assert cost["slippage_provenance"]["fill_observed"] is False
    assert cost["direction_aware_methodology"]["direction_aware"] is True


def test_prereg_is_one_untuned_research_only_baseline():
    prereg = PREREG.read_text(encoding="utf-8")
    assert "STBS020-MODEL0-TRAIN-001" in prereg
    assert "PF after x1 costs strictly greater than 1.30" in prereg
    assert "Optimization, WFA, OOS, holdout, Monte Carlo, paper, live, promotion" in prereg
    assert "Parent HYP019 terminal raw-row SHA256 is `F5A1072893D887E0E8A6EDF3538DC85F4D8B37222CF27A5A4DBDEDADF7C0FBC1`" in prereg
