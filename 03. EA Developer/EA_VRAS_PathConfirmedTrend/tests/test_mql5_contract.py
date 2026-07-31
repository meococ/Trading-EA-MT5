from __future__ import annotations

import json
from pathlib import Path
import re


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "EA_VRAS_PathConfirmedTrend.mq5"


def text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_and_variant_pair_are_fail_closed() -> None:
    source = text()
    assert 'EA_NAME="EA_VRAS_PathConfirmedTrend"' in source
    assert 'InpHypothesisId="HYP-VRAS-EURUSD-M5-004"' in source
    assert "InpMagic=5600744" in source
    assert 'InpVariantTag!="CHALLENGER_PATH_CONFIRM"' in source
    assert 'InpVariantTag!="CONTROL_IMMEDIATE_TREND"' in source
    assert source.count("HYP-VRAS-EURUSD-M5-004") >= 2
    assert source.count("5600744") >= 2


def test_path_confirmation_surface_is_explicit() -> None:
    source = text()
    for token in (
        "InpUsePathConfirmation",
        "ArmPendingTrend",
        "ResolvePendingTrend",
        "RefreshConfirmationState",
        "PATH_CANDIDATE_ARMED",
        "PATH_CONFIRM_ACCEPTED",
        "PATH_CONFIRM_REJECT",
        "path_candidates_armed",
        "path_confirmations_passed",
        "path_confirmations_rejected",
        "path_confirmations_expired",
    ):
        assert token in source


def test_confirmation_is_closed_bar_and_one_bar_only() -> None:
    source = text()
    assert "CopyRates(_Symbol,PERIOD_M5,1,3,bars)" in source
    assert "current_bar!=pending.decision_server+PeriodSeconds(PERIOD_M5)" in source
    assert "bars[0].close<=pending.high1" in source
    assert "bars[0].close>=pending.low1" in source
    assert not re.search(r"CopyBuffer\([^\n]+,\s*0\s*,\s*1", source)


def test_range_remains_immediate_but_trend_arms_in_challenger() -> None:
    source = text()
    range_branch = source.index("if(state.signal==SIGNAL_RANGE_LONG || state.signal==SIGNAL_RANGE_SHORT)")
    trend_branch = source.index("if(state.signal==SIGNAL_TREND_LONG || state.signal==SIGNAL_TREND_SHORT)", range_branch)
    assert "TryOpenTrade(state)" in source[range_branch:trend_branch]
    assert "ArmPendingTrend(state)" in source[trend_branch:]


def test_contract_and_diagnostic_boundary() -> None:
    contract = json.loads((PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json").read_text(encoding="utf-8"))
    assert contract["telemetry_profile"] == "lifecycle-v3"
    assert contract["variant_tag_input"] == "InpVariantTag"
    source = text()
    assert r'\"promotion_eligible\":false' in source
    assert r'\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\"' in source
    assert "PositionModify" not in source
    assert "PositionClosePartial" not in source
