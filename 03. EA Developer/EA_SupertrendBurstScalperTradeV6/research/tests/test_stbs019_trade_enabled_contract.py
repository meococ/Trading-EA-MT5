from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
V5 = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV5/EA_SupertrendBurstScalperTradeV5.mq5"
PACKAGE = Path(__file__).resolve().parents[2]
V6 = PACKAGE / "EA_SupertrendBurstScalperTradeV6.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COST = PACKAGE / "research/HYP-STBS-XAUUSD-M15-019_RESEARCH_COST_SOURCE_MANIFEST.json"


def source() -> str:
    return V6.read_text(encoding="utf-8")


def test_v6_is_exact_bounded_v5_revision():
    text = source()
    normalized = (text
        .replace('       InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604119 ||', '       !InpAuditOnly || InpEnableTelemetry || InpMagic!=5604116 ||')
        .replace('#property version   "6.00"', '#property version   "5.00"')
        .replace('#property description "H1 Supertrend flip trade baseline with account-safe margin and lifecycle-v3 evidence."', '#property description "H1 Supertrend flip with account-compatible margin safety and bounded audit evidence."')
        .replace('HYP-STBS-XAUUSD-M15-019', 'HYP-STBS-XAUUSD-M15-016')
        .replace('STBS_H1_FLIP_M15_BURST_TRADE_V6_ACCOUNT_SAFE', 'STBS_H1_FLIP_M15_BURST_AUDIT_V5_ACCOUNT_SAFE')
        .replace('input bool   InpEnableTelemetry     = true;', 'input bool   InpEnableTelemetry     = false;')
        .replace('input long   InpMagic               = 5604119;', 'input long   InpMagic               = 5604116;')
        .replace('EA_SupertrendBurstScalperTradeV6', 'EA_SupertrendBurstScalperTradeV5'))
    assert normalized == V5.read_text(encoding="utf-8")


def test_trade_identity_and_lifecycle_defaults_are_frozen():
    text = source()
    assert 'input bool   InpAuditOnly           = false;' in text
    assert 'input bool   InpEnableTelemetry     = true;' in text
    assert 'InpHypothesisId!="HYP-STBS-XAUUSD-M15-019"' in text
    assert 'InpVariantTag!="STBS_H1_FLIP_M15_BURST_TRADE_V6_ACCOUNT_SAFE"' in text
    assert 'InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604119' in text
    assert json.loads(CONTRACT.read_text(encoding="utf-8"))["telemetry_profile"] == "lifecycle-v3"


def test_trade_gateways_and_lifecycle_evidence_exist():
    text = source()
    assert text.count("OrderSend(request,result)") == 3
    assert "bool OpenTelemetry()" in text
    assert "bool ReconcileLifecycleHistory()" in text
    assert "WriteRunMeta()" in text
    assert "g_lifecycle_positions_opened!=g_lifecycle_positions_final_closed" in text
    assert '\\"runtime_failed\\":%s' in text


def test_frozen_signal_risk_and_design_contract_survives():
    text = source()
    for needle in (
        "const int ST_ATR_PERIOD          = 10;", "const double ST_FACTOR           = 3.0;",
        "const int M15_ATR_PERIOD         = 14;", "input double InpRiskPercent         = 0.25;",
        "input double InpStopAtrMult         = 1.00;", "input double InpTargetRR            = 1.50;",
        "input int    InpMaxHoldBars         = 8;", "DESIGN_START_TIME", "DESIGN_END_TIME",
        "InpMoneyHeadroomReserveFactor   = 0.20", "InpMaxNewPositionMarginPct     = 5.00",
    ):
        assert needle in text


def test_cost_manifest_is_research_only_and_identity_exact():
    cost = json.loads(COST.read_text(encoding="utf-8"))
    assert cost["evidence_tier"] == "RESEARCH_PROXY"
    assert cost["promotion_eligible"] is False
    assert cost["account_fingerprint"] == "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"
    assert cost["data_fingerprint"] == "B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25"
    assert cost["run_meta_contract"]["hypothesis_id"] == "HYP-STBS-XAUUSD-M15-019"
    assert cost["run_meta_contract"]["magic"] == 5604119
    assert cost["slippage_provenance"]["fill_observed"] is False
