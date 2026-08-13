from __future__ import annotations

import re
from pathlib import Path


EA = Path(__file__).resolve().parents[2] / "EA_PriorDayVolumeProfileReentry.mq5"
CONTRACT = EA.with_name("ALPHAFACTORY_EA_CONTRACT.json")


def source() -> str:
    return EA.read_text(encoding="utf-8")


def test_frozen_identity_timeframe_and_point_contract() -> None:
    text = source()
    assert 'EXPECTED_HYPOTHESIS="HYP-PVPR-EURUSD-M15-002"' in text
    assert 'EXPECTED_SYMBOL="EURUSD"' in text
    assert "_Period!=PERIOD_M15" in text
    assert "const double BROKER_POINT=0.00001" in text
    assert "const double PROFILE_PIP=0.0001" in text
    assert "InpMagic!=5604602" in text


def test_profile_formula_and_integer_boundaries_match_source() -> None:
    text = source()
    assert "(rates[i].high+rates[i].low+rates[i].close)/3.0" in text
    assert "MathFloor(price/PROFILE_PIP+0.5)" in text
    assert "MathFloor(price/BROKER_POINT+0.5)" in text
    assert "const double VALUE_AREA_FRACTION=0.70" in text
    assert "lower_volume>=upper_volume" in text
    assert "open_points<profile.val_points" in text
    assert "open_points>profile.vah_points" in text
    assert "close_points>=profile.val_points && close_points<=profile.vah_points" in text


def test_closed_bar_and_exact_next_only() -> None:
    text = source()
    assert "CopyRates(_Symbol,PERIOD_M15,1,1,source)" in text
    assert "availability_time-source[0].time)!=900" in text
    assert "availability_utc-source_utc)!=900" in text
    assert "CopyRates(_Symbol,PERIOD_M1,1,PROFILE_LOOKBACK_M1,rates)" in text
    assert "CopyRates(_Symbol,PERIOD_M15,0" not in text


def test_execution_mapping_is_frozen_and_untuned() -> None:
    text = source()
    assert "source[0].low-PROFILE_PIP" in text
    assert "source[0].high+PROFILE_PIP" in text
    assert "const double TARGET_R=1.50" in text
    assert "const int MAX_HOLD_M15_BARS=16" in text
    assert "equity*(InpRiskPercent/100.0)/MathAbs(loss_one_lot)" in text
    for forbidden in ("Trailing", "BreakEven", "Optimization", "OnTester"):
        assert forbidden not in text


def test_signal_summary_exposes_parity_and_execution_funnel() -> None:
    text = source()
    assert "PVPR002_SIGNAL source=" in text
    assert "open_points=%I64d" in text
    assert "PVPR002_SUMMARY" in text
    for field in (
        "valid_profiles=", "raw=", "long=", "short=", "entries=",
        "entry_rejects=", "geometry_rejects=", "risk_lock_skips=", "open_position=",
    ):
        assert field in text


def test_no_current_bar_signal_reads_or_indicator_lookahead() -> None:
    text = source()
    assert not re.search(r"CopyRates\([^\n]+PERIOD_M15\s*,\s*0\s*,", text)
    assert "iHigh(" not in text
    assert "iLow(" not in text
    assert "iClose(" not in text
    assert "CopyBuffer(" not in text


def test_contract_is_telemetry_none_and_not_promotion_ready() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert '"telemetry_profile": "none"' in text
    assert '"timeframe": "M15"' in text
    assert '"expected_symbol": "EURUSD"' in text
    assert '"promotion_eligible": false' in text
