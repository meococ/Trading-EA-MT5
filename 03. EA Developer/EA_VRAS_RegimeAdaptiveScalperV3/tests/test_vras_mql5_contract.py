from __future__ import annotations

import json
from pathlib import Path
import re


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "EA_VRAS_RegimeAdaptiveScalperV3.mq5"


def text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_contract_declares_lifecycle_and_variant() -> None:
    contract = json.loads((PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["telemetry_profile"] == "lifecycle-v3"
    assert contract["variant_tag_input"] == "InpVariantTag"


def test_exact_identity_and_frozen_defaults() -> None:
    source = text()
    for token in (
        'EA_NAME="EA_VRAS_RegimeAdaptiveScalperV3"',
        'InpHypothesisId="HYP-VRAS-EURUSD-M5-003"',
        "InpMagic=5600743",
        "InpAdxEnter=25.0",
        "InpAdxExit=19.0",
        "InpMinRegimeDwellBars=6",
        "InpWarmupBars=15",
        "InpSdFloorAtr=0.30",
        "InpCostDistanceMultiple=8.0",
        "InpMaxSpreadPips=1.20",
        "InpRiskPercent=0.25",
    ):
        assert token in source
    assert source.count("HYP-VRAS-EURUSD-M5-003") >= 2
    assert source.count("5600743") >= 2
    assert "HYP-VRAS-EURUSD-M5-001" not in source
    assert "HYP-VRAS-EURUSD-M5-002" not in source


def test_closed_bar_only_and_confirmed_fractal() -> None:
    source = text()
    assert "iTime(_Symbol,PERIOD_M5,0)" in source
    assert "CopyRates(_Symbol,PERIOD_M5,1" in source
    assert "ReadIndicator(g_adx_handle,0,state.adx" in source
    assert "ReadIndicator(g_atr_handle,0,state.atr" in source
    assert "ReadIndicator(g_rsi_handle,0,state.rsi" in source
    assert "CopyBuffer(handle,buffer,1,1,values)" in source
    assert "for(int center=2;" in source
    assert "bars[center-2]" in source and "bars[center+2]" in source
    assert not re.search(r"CopyBuffer\([^\n]+,\s*0\s*,\s*1", source)


def test_seven_gap_modules_are_explicit() -> None:
    source = text()
    for token in (
        "UpdateRegime",
        "WeightedWelfordAdd",
        "ComputeSessionStats",
        "SessionAnchorUtc",
        "FindConfirmedAnchor",
        "ComputeAnchoredVwap",
        "EvaluateSignal",
        "CostDistanceAllows",
        "ServerToUtc",
        "IsEuropeDstUtc",
        "IsUsDstUtc",
    ):
        assert token in source


def test_regime_root_and_symmetric_range_rules() -> None:
    source = text()
    assert "if(g_regime==REGIME_RANGE)" in source
    assert "state.rsi>InpRsiLongFloor" in source
    assert "state.rsi<InpRsiShortCeiling" in source
    assert "if(g_regime==REGIME_TREND)" in source
    assert "state.close1>state.session_vwap" in source
    assert "state.close1<state.session_vwap" in source


def test_execution_preflight_and_no_plan_mutation() -> None:
    source = text()
    assert "OrderCheck(request,check)" in source
    assert "OrderSend(request,result)" in source
    assert source.index("OrderCheck(request,check)") < source.index("OrderSend(request,result)")
    assert "check.retcode!=TRADE_RETCODE_DONE" not in source
    assert 'PrintFormat("VRAS OrderCheck rejected retcode=%u' in source
    assert "PositionModify" not in source
    assert "PositionClosePartial" not in source
    assert "martingale" not in source.lower()


def test_diagnostic_boundary_and_lifecycle_sidecars() -> None:
    source = text()
    assert r'\"promotion_eligible\":false' in source
    assert r'\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\"' in source
    assert 'StringFormat("%s_LifecycleTrades_%s.csv"' in source
    assert 'StringFormat("%s_RunMeta_%s.json"' in source
    assert "alphafactory_run_meta.v1" in source
