from __future__ import annotations

import hashlib
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "EA_LSSOBPropScalper.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
RESEARCH = PACKAGE / "research"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_owner_override_plan_and_matrix_are_hash_bound() -> None:
    plan = RESEARCH / "HYP-LSS-OB-REPL-MT5-EURUSD-M15-002_MT5_PLAN.md"
    matrix = RESEARCH / "HYP-LSS-OB-REPL-MT5-EURUSD-M15-002_REQUIREMENT_MATRIX.md"
    assert sha256(plan) == "0514AAF3D99EECFDF849A6814D18A39A901E32F62CC2A5D276B14D11FAE27ED0"
    assert sha256(matrix) == "9EE82A981FB536E35F5F6737A7ADE8D6146AD3CE5CD377B1A1849A48C924E9E8"


def test_package_declares_lifecycle_and_variant_tag() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert '"telemetry_profile": "lifecycle-v3"' in text
    assert '"variant_tag_input": "InpSignalMode"' in text


def test_exact_identity_and_two_fixed_variants() -> None:
    text = source_text()
    assert 'HYP-LSS-OB-REPL-MT5-EURUSD-M15-002' in text
    assert "SIGNAL_CONTROL=0" in text
    assert "SIGNAL_LSS_OB_CHALLENGER=1" in text
    assert "SetupState g_setup;" in text
    assert "g_setups" not in text


def test_m15_closed_bar_and_custom_utc_context_contract() -> None:
    text = source_text()
    assert "_Period!=PERIOD_M15" in text
    assert "iTime(_Symbol,PERIOD_M15,0)" in text  # new-bar gate only
    assert "CopyRates(_Symbol,PERIOD_M15,1" in text
    assert "CopyBuffer(g_adx_handle,0,1,1" in text
    assert "CopyBuffer(g_atr_handle,0,1,1" in text
    assert "BuildClosedUtcBars(60" in text
    assert "BuildClosedUtcBars(240" in text
    assert "CLOCK_CONTRACT=\"fivepercent_eu_dst_server_to_utc_custom_h1_h4\"" in text
    assert "PERIOD_M5" not in text


def test_signal_geometry_is_frozen() -> None:
    text = source_text()
    for token in (
        "InpPivotStrength=2",
        "InpSweepLookback=20",
        "InpDisplacementBars=3",
        "InpDisplacementAtrMultiple=1.80",
        "InpRetestBars=12",
        "InpConfirmationBodyRatio=0.60",
        "InpConfirmationOuterFraction=0.25",
        "InpStopBufferPips=1.50",
        "InpMinStopPips=8.00",
        "InpMaxStopPips=12.00",
        "InpTargetRR=2.00",
    ):
        assert token in text
    assert "body<InpDisplacementAtrMultiple*atr" in text
    assert "MathMin(g_setup.sweep_low,ob.low)" in text
    assert "MathMax(g_setup.sweep_high,ob.high)" in text


def test_risk_session_news_and_fixed_exit_contract() -> None:
    text = source_text()
    assert "LONDON_END_UTC_MIN=10*60" in text
    assert "NEW_YORK_END_UTC_MIN=16*60" in text
    assert "InpMaxSpreadPips=1.80" in text
    assert "InpFlattenUtcHour=21" in text
    assert "InpFlattenUtcMinute=45" in text
    assert "risk_pips<InpMinStopPips || risk_pips>InpMaxStopPips" in text
    assert "NewsBlocked(server_time)" in text
    assert "NEWS_CALENDAR_SOURCE_SHA256" in text
    assert "BreakEven" not in text
    assert "AtrTrail" not in text
    assert "PositionModify" not in text


def test_news_calendar_accepts_distinct_events_sharing_one_epoch() -> None:
    text = source_text()
    assert "NEWS_CALENDAR_UTC[index]<NEWS_CALENDAR_UTC[index-1]" in text
    assert "NEWS_CALENDAR_UTC[index]<=NEWS_CALENDAR_UTC[index-1]" not in text


def test_runmeta_binds_report_data_clock_and_diagnostic_boundary() -> None:
    text = source_text()
    assert "REPORT_SHA256" in text
    assert "SOURCE_DATA_SHA256" in text
    assert r'\"cost_status\":\"UNVERIFIED_DIAGNOSTIC\"' in text
    assert r'\"promotion_eligible\":false' in text
