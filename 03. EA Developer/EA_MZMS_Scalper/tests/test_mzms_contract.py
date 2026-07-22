from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_MZMS_Scalper.mq5"
PLAN = ROOT / "research" / "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_FROZEN_PREREG.md"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_source_exists_and_binds_identity():
    text = source_text()
    assert 'const string EA_NAME="EA_MZMS_Scalper"' in text
    assert 'input string           InpHypothesisId=' in text
    assert "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006" in text
    assert "HYP-MZMS-XAU-M5-007" in text
    assert "HYP-MZMS-XAU-M5-008" in text
    assert "HYP-MZMS-XAU-M5-009" in text
    assert "HYP-MZMS-XAU-M5-010" in text
    assert 'const string TELEMETRY_PROFILE="lifecycle-v3"' in text
    assert 'const string SOURCE_DATA_SHA256="BC45C0CC644CE8BE67FF61245F20F8063BE2BAE99FEFF77D25556CC1F955B563"' in text


def test_closed_bar_indicator_reads_and_new_bar_gate_only():
    text = source_text()
    assert "iTime(_Symbol,PERIOD_M5,0)" in text
    assert "if(handle==INVALID_HANDLE || shift<1)" in text
    assert "CopyBuffer(handle,buffer,shift,1,values)" in text
    assert "CopyRates(_Symbol,PERIOD_M5,1,SIGNAL_RATES_BARS,bars)" in text
    # no live-bar signal buffer reads
    assert not re.search(r"CopyBuffer\([^\n]+,\s*0\s*,\s*1", text)
    assert "shift<1" in text


def test_local_extremum_and_normalized_delta_are_mandatory():
    text = source_text()
    assert "hist1>hist2 && hist2<hist3 && hist2<=0.0" in text
    assert "hist1<hist2 && hist2>hist3 && hist2>=0.0" in text
    assert "InpMinHistDeltaAtr=0.01" in text
    assert "delta_atr<InpMinHistDeltaAtr" in text


def test_cluster_guard_and_break_even_default_off():
    text = source_text()
    assert "InpCooldownBars=5" in text
    assert "CooldownAllows" in text
    assert "InpUseBreakEven=false" in text
    assert "if(InpUseBreakEven)" in text
    assert "return false;" in text


def test_session_is_utc_with_europe_dst_conversion():
    text = source_text()
    assert "InpServerUtcOffsetWinterHours=2" in text
    assert "InpServerUsesEuropeDst=true" in text
    assert "ServerToUtc" in text
    assert "InpSessionStartUtcHour=8" in text
    assert "InpSessionEndUtcHour=17" in text


def test_entry_spread_is_checked_in_pips_and_zero_fails():
    text = source_text()
    assert "InpMaxSpreadPips=35.00" in text
    assert "spread<=0.0 || spread>InpMaxSpreadPips" in text


def test_frozen_management_contract():
    text = source_text()
    assert "InpStopLookbackBars=5" in text
    assert "InpStopAtrMultiple=1.50" in text
    assert "InpStopBufferPips=40.00" in text
    assert "InpTargetRR=1.60" in text
    assert "InpMaxHoldBars=15" in text


def test_control_and_challenger_and_modes_2_to_5_are_explicit():
    text = source_text()
    assert "SIGNAL_CONTROL=0" in text
    assert "SIGNAL_MZMS_CHALLENGER=1" in text
    assert "SIGNAL_IMPULSE_INIT=2" in text
    assert "SIGNAL_PULLBACK_RECLAIM=3" in text
    assert "SIGNAL_SQUEEZE_BREAK=4" in text
    assert "SIGNAL_EXHAUST_REJECT=5" in text
    assert "InpSignalMode" in text
    assert "ClosedBarSignalImpulse007" in text
    assert "ClosedBarSignalPullback008" in text
    assert "ClosedBarSignalSqueeze009" in text
    assert "ClosedBarSignalExhaust010" in text


def test_hypothesis_and_magic_fail_closed_mapping():
    text = source_text()
    assert "ExpectedHypothesisId" in text
    assert "ExpectedMagic" in text
    assert "if(InpHypothesisId!=ExpectedHypothesisId(InpSignalMode))" in text
    assert "if(InpMagic!=ExpectedMagic(InpSignalMode))" in text
    assert "return 5600727" in text
    assert "return 5600728" in text
    assert "return 5600729" in text
    assert "return 5600730" in text
    assert "return 5600722" in text


def test_state_telemetry_sidecar_contract():
    text = source_text()
    assert 'StringFormat("%s_StateTelemetry_%s.csv",_Symbol,g_run_id)' in text
    assert "WriteStateTelemetryAccepted" in text
    assert "g_state_telemetry_handle" in text
    assert "donchian_high20" in text
    assert "bb_width2" in text
    assert "pivot_shift" in text
    assert "wick_upper_frac" in text
    assert "g_squeeze_pre" in text
    assert "lifecycle-v3" in text
    assert "alphafactory_run_meta.v1" in text


def test_mode_specific_frozen_rules_present():
    text = source_text()
    # mode2 Donchian
    assert "Donchian" in text or "donchian_high20" in text
    assert "1.20*state.body_median_ref" in text
    assert "0.55*range1" in text
    assert "state.adx1>=16.0 && state.adx1<=32.0" in text
    # mode3 pullback
    assert "IsPivotLow" in text
    assert "IsPivotHigh" in text
    assert "0.40" in text and "1.80" in text
    assert "g_anti_break_long" in text
    # mode4 squeeze
    assert "iBands(_Symbol,PERIOD_M5,20,0,2.0,PRICE_CLOSE)" in text
    assert "state.atr_rank_count<=8" in text
    assert "0.85*state.bb_width_median_ref" in text
    # mode5 exhaustion
    assert "state.rsi1>=70.0" in text
    assert "state.rsi1<=30.0" in text
    assert "0.55*range1" in text
    assert "state.adx1<state.adx2" in text


def test_no_intrabar_signal_or_trailing_or_partials():
    text = source_text()
    assert "PositionClosePartial" not in text
    assert "Trailing" not in text and "trailing" not in text
    assert "iTime(_Symbol,PERIOD_M5,0)" in text
    assert "if(current_bar==g_last_m5_bar)" in text


def test_plan_forbids_intrabar_and_be_arm():
    text = PLAN.read_text(encoding="utf-8")
    assert "intrabar indicator evaluation" in text.lower()
    assert "Break-even OFF" in text
    assert "BE/intrabar arm" in text


def test_owner_xau_transfer_freezes_geometry_and_disables_news_uniformly():
    text = PLAN.read_text(encoding="utf-8")
    assert "2018.01.01" in text
    assert "2026.07.21" in text
    assert "InpRequireNewsGuard=false" in text
    assert "XAUUSD" in text
    assert "InpMaxSpreadPips=35.00" in text
    assert "InpStopBufferPips=40.00" in text
    assert "post-outcome cross-symbol transfer" in text
    assert "USD 100,000" in text
