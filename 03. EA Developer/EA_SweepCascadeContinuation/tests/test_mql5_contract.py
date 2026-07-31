from __future__ import annotations

import json
from pathlib import Path
import re


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "EA_SweepCascadeContinuation.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
PREREG = (
    PACKAGE
    / "research"
    / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_FROZEN_PREREG.md"
)


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_and_pair_fail_closed() -> None:
    source = source_text()
    assert 'EA_NAME="EA_SweepCascadeContinuation"' in source
    assert (
        'InpHypothesisId="HYP-SCC-MT5-REPLICATION-EURUSD-M5-004"' in source
    )
    assert "InpMagic=5600754" in source
    assert 'InpVariantTag!="CONTROL_FIRST_CLOSE_BREAK"' in source
    assert 'InpVariantTag!="CHALLENGER_HOLD_RETEST"' in source
    assert source.count("5600754") >= 2


def test_closed_bar_pivot_and_break_contract() -> None:
    source = source_text()
    assert "CopyRates(_Symbol,PERIOD_M5,1,6,bars)" in source
    assert "RefreshConfirmedPivots" in source
    assert "DetectBreak" in source
    assert "candidate_shift=4" in source
    assert "bars[0].time-bars[1].time!=PeriodSeconds(PERIOD_M5)" in source
    assert not re.search(r"CopyBuffer\([^,]+,[^,]+,\s*0\s*,", source)


def test_hold_retest_priority_and_geometry_are_explicit() -> None:
    source = source_text()
    for token in (
        "ResolveHold",
        "ResolveRetest",
        "REJECT_GAP",
        "REJECT_DAY_BOUNDARY",
        "REJECT_CLOSE_INSIDE",
        "ACCEPT_RETEST",
        "EXPIRE_12",
        "InpRetestBars=12",
        "InpStopAtrBuffer=0.25",
        "MathMin(g_candidate.break_low,MathMin(g_candidate.hold_low,bar.low))",
        "MathMax(g_candidate.break_high,MathMax(g_candidate.hold_high,bar.high))",
    ):
        assert token in source


def test_execution_contract_has_no_hidden_management() -> None:
    source = source_text()
    for token in (
        "InpRiskPercent=0.01",
        "InpTargetR=2.00",
        "InpMaxHoldBars=24",
        "InpMaxSpreadPips=2.00",
        "RiskSizedVolume",
        "OrderCheck",
        "ManageOwnedPosition",
    ):
        assert token in source
    assert "PositionModify" not in source
    assert "PositionClosePartial" not in source


def test_capability_and_diagnostic_boundary() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract == {
        "schema_version": "alphafactory_ea_contract.v1",
        "telemetry_profile": "lifecycle-v3",
        "market_phase_adapter": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "variant_tag_input": "InpVariantTag",
    }
    source = source_text()
    assert r'\"promotion_eligible\":false' in source
    assert r'\"cost_status\":\"UNVERIFIED_DIAGNOSTIC_ONLY\"' in source
    assert r'\"news_status\":\"DISABLED_MATCHED\"' in source


def test_prereg_keeps_parent_park_and_exact_pair() -> None:
    prereg = PREREG.read_text(encoding="utf-8")
    assert "scale-only diagnostic child" in prereg
    assert "`InpRiskPercent`: `0.05` to `0.01`" in prereg
    assert "CONTROL_FIRST_CLOSE_BREAK" in prereg
    assert "CHALLENGER_HOLD_RETEST" in prereg
    assert "promotion_eligible=false" in prereg
    assert "No threshold, time, weekday, direction, stop, target or subgroup rescue" in prereg
