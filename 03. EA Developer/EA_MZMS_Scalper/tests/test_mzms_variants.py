from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_MZMS_Scalper.mq5"
PRESETS = ROOT / "presets"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_mode_dispatcher_covers_all_six_modes():
    text = source_text()
    for name in (
        "ClosedBarSignalControl",
        "ClosedBarSignalLegacyMzms",
        "ClosedBarSignalImpulse007",
        "ClosedBarSignalPullback008",
        "ClosedBarSignalSqueeze009",
        "ClosedBarSignalExhaust010",
    ):
        assert name in text
    assert "if(InpSignalMode==SIGNAL_CONTROL)" in text
    assert "else if(InpSignalMode==SIGNAL_MZMS_CHALLENGER)" in text
    assert "else if(InpSignalMode==SIGNAL_IMPULSE_INIT)" in text
    assert "else if(InpSignalMode==SIGNAL_PULLBACK_RECLAIM)" in text
    assert "else if(InpSignalMode==SIGNAL_SQUEEZE_BREAK)" in text
    assert "else if(InpSignalMode==SIGNAL_EXHAUST_REJECT)" in text


def test_mode2_donchian_excludes_shift1_from_channel():
    text = source_text()
    assert "for(int i=2;i<=20;i++)" in text
    assert "state.donchian_high20=bars[1].high" in text
    assert "state.donchian_low20=bars[1].low" in text
    assert "state.c1>state.donchian_high20" in text
    assert "state.c1<state.donchian_low20" in text


def test_mode3_pivot_search_window_and_anti_break():
    text = source_text()
    assert "for(int p=3;p<=8;p++)" in text
    assert "g_anti_break_long" in text
    assert "g_anti_break_short" in text
    assert "0.05*state.atr1" in text
    assert "0.15*state.atr1" in text


def test_mode4_compression_measured_on_shift2_not_break_bar():
    text = source_text()
    assert "state.atr_rank_count" in text
    assert "for(int j=3;j<=34;j++)" in text
    assert "state.bb_width2=" in text
    assert "MedianSorted(widths,20)" in text
    assert "state.adx2<=28.0" in text
    assert "state.adx1<35.0" in text


def test_mode5_fade_requires_falling_adx_and_extreme_rsi():
    text = source_text()
    assert "state.rsi1>=70.0" in text
    assert "state.rsi1<=30.0" in text
    assert "state.adx1<state.adx2" in text
    assert "state.g_run_up" in text
    assert "state.g_run_down" in text
    assert "0.55*range1" in text


def test_legacy_mode1_surface_still_present():
    text = source_text()
    assert "ClosedBarSignalLegacyMzms" in text
    assert "hist1>hist2 && hist2<hist3 && hist2<=0.0" in text
    assert "InpMinHistDeltaAtr" in text
    assert "InpRsiLower" in text


def test_readindicator_rejects_shift_zero():
    text = source_text()
    assert "if(handle==INVALID_HANDLE || shift<1)" in text
    assert "default: return false;" in text
    # Variable-shift CopyBuffer is not auditor-provable closed-bar (code only).
    stripped = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    assert not re.search(r"CopyBuffer\s*\(\s*handle\s*,\s*buffer\s*,\s*shift\s*,", stripped)


def test_copybuffer_uses_literal_closed_bar_shifts():
    """Every CopyBuffer decision read must use a positive integer literal shift."""
    text = source_text()
    # Strip line comments only; CopyBuffer sites are single-line in this EA.
    stripped = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    calls = re.findall(r"CopyBuffer\s*\(([^;]*?)\)", stripped)
    assert calls, "expected at least one CopyBuffer call"
    for body in calls:
        args = [a.strip() for a in body.split(",")]
        assert len(args) >= 3, body
        shift_expr = args[2]
        assert re.fullmatch(r"[1-9]\d*", shift_expr), (
            f"CopyBuffer shift must be literal closed-bar integer, got: {shift_expr!r}"
        )
    # Auditor-equivalent: all live CopyBuffer shifts are positive integer literals.
    assert any(re.fullmatch(r"[1-9]\d*", a.strip().split(",")[2].strip()) for a in calls)


def test_state_telemetry_uses_string_line_not_overlong_filewrite():
    text = source_text()
    assert "WriteStateTelemetryAccepted" in text
    assert "FileWriteString(g_state_telemetry_handle" in text
    assert 'StringFormat("%s_StateTelemetry_%s.csv",_Symbol,g_run_id)' in text


def test_four_presets_exist_with_unique_identity():
    rows = [
        ("HYP-MZMS-XAU-M5-007.set", "2", "HYP-MZMS-XAU-M5-007", "5600727"),
        ("HYP-MZMS-XAU-M5-008.set", "3", "HYP-MZMS-XAU-M5-008", "5600728"),
        ("HYP-MZMS-XAU-M5-009.set", "4", "HYP-MZMS-XAU-M5-009", "5600729"),
        ("HYP-MZMS-XAU-M5-010.set", "5", "HYP-MZMS-XAU-M5-010", "5600730"),
    ]
    for name, mode, hyp, magic in rows:
        path = PRESETS / name
        assert path.is_file(), name
        text = path.read_text(encoding="utf-8")
        assert f"InpSignalMode={mode}" in text
        assert hyp in text
        assert magic in text
        assert "InpUseBreakEven=false" in text
        assert "InpRequireNewsGuard=false" in text
        assert "InpMaxSpreadPips=35" in text
        assert "InpStopBufferPips=40" in text
