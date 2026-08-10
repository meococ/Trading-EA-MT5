from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "03. EA Developer/EA_CBRK_XAUBreakout/EA_CBRK_XAUBreakout.mq5"
PREREG = ROOT / "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/HYP-CBRK-XAUUSD-M5-002_FROZEN_PREREG.md"
DQ_PREREG = ROOT / "03. EA Developer/EA_LOMX_MultiAssetMomentum/research/HYP-CBRK-XAUUSD-M5-DQ-002_FROZEN_PREREG.md"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8-sig")


def on_tick_body(text: str) -> str:
    start = text.index("void OnTick()")
    return text[start:]


def session_eligible(hour: int, minute: int, weekday: int = 1) -> bool:
    minute_of_day = hour * 60 + minute
    return weekday not in (0, 6) and 420 <= minute_of_day < 960


def test_frozen_prereg_declares_only_clock_correction_and_exact_dq_population():
    prereg = PREREG.read_text(encoding="utf-8-sig")
    dq = DQ_PREREG.read_text(encoding="utf-8-sig")
    assert "HYP-CBRK-XAUUSD-M5-002" in prereg
    assert "ServerToUtc(rates[0].time)" in prereg
    assert "rates[1]" in prereg
    assert "00:00` through `05:55" in prereg
    assert "HYP-CBRK-XAUUSD-M5-DQ-002" in dq
    assert "exactly `351303` bars" in dq
    assert "no boundary convention" in dq


def test_signal_session_uses_just_closed_bar_after_closed_bars_load():
    body = on_tick_body(source_text())
    load = body.index("if(!LoadClosedBars(rates))")
    signal = body.index("datetime signal_utc=ServerToUtc(rates[0].time);")
    gate = body.index("signal_minute_of_day<InpTradeStartMinutesUtc")
    risk = body.index("if(g_daily_locked || g_account_dd_locked)")
    assert load < signal < gate < risk
    assert "TimeToStruct(signal_utc,signal_parts);" in body
    assert "LoadExactAsianRange(signal_utc,asian_high,asian_low)" in body


def test_fresh_package_identity_is_explicit_and_parent_source_stays_frozen():
    text = source_text()
    parent = ROOT / "03. EA Developer/EA_LOMX_MultiAssetMomentum/EA_LOMX_MultiAssetMomentum.mq5"
    assert 'const string EA_NAME="EA_CBRK_XAUBreakout";' in text
    assert 'CBRK XAUUSD M5 compression breakout clock-fixed EA' in text
    assert parent.read_bytes() != SOURCE.read_bytes()
    import hashlib
    assert hashlib.sha256(parent.read_bytes()).hexdigest().upper() == "D363121DC7FFCB128A67C796B76F8B86C8AB2262FF045EAC62B49FE19FB3298B"


def test_decision_clock_is_not_used_for_entry_session_gate():
    body = on_tick_body(source_text())
    session_block = body[body.index("MqlDateTime signal_parts;"): body.index("if(g_daily_locked || g_account_dd_locked)")]
    assert "utc_now" not in session_block
    assert "utc_parts" not in session_block
    assert "rates[1].time" not in body


def test_session_boundaries_are_signal_bar_boundaries():
    assert not session_eligible(6, 55)
    assert session_eligible(7, 0)
    assert session_eligible(15, 55)
    assert not session_eligible(16, 0)
    assert not session_eligible(12, 0, weekday=0)
    assert not session_eligible(12, 0, weekday=6)


def test_breakout_arithmetic_and_execution_risk_contract_remain_present():
    text = source_text()
    required = [
        "bar2_range<BREAKOUT_CONTRACTION_RATIO*prior_range_mean",
        "for(int i=1;i<=15;i++)",
        "rates[0].tick_volume<=prior_volume_mean",
        "rates[0].close>box_high+BREAKOUT_BUFFER_ATR_MULT*atr",
        "rates[0].close<box_low-BREAKOUT_BUFFER_ATR_MULT*atr",
        "signal.stop=box_low-BREAKOUT_STOP_ATR_MULT*atr",
        "signal.stop=box_high+BREAKOUT_STOP_ATR_MULT*atr",
        "held_bars>=InpMaxHoldBars",
        "AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0",
    ]
    for anchor in required:
        assert anchor in text
    assert re.search(r"CopyRates\(_Symbol,PERIOD_M5,1,CLOSED_BAR_COUNT,rates\)==CLOSED_BAR_COUNT", text)
