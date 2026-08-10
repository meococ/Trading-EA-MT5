from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "03. EA Developer/EA_DonchianChandelierBreakout/EA_DonchianChandelierBreakout.mq5"
PREREG = ROOT / "03. EA Developer/EA_DonchianChandelierBreakout/research/HYP-DCX-XAUUSD-M15-001_FROZEN_PREREG.md"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_and_parameters_are_frozen() -> None:
    text = source()
    for token in (
        'EXPECTED_HYPOTHESIS="HYP-DCX-XAUUSD-M15-001"',
        'EXPECTED_SYMBOL="XAUUSD"',
        "DONCHIAN_LENGTH=20", "CHANDELIER_LENGTH=22", "ATR_PERIOD=22",
        "CHANDELIER_ATR_MULTIPLIER=3.0", "InpMagic=5603801",
        "DESIGN_FROM=D'2010.01.04 00:00'", "DESIGN_TO=D'2018.01.01 00:00'",
    ):
        assert token in text


def test_closed_bar_transition_excludes_release_bar_from_channel() -> None:
    text = source()
    assert "HighestHigh(rates,current-DONCHIAN_LENGTH,current-1)" in text
    assert "LowestLow(rates,current-DONCHIAN_LENGTH,current-1)" in text
    assert "rates[current].close>upper && rates[previous].close<=previous_upper" in text
    assert "rates[current].close<lower && rates[previous].close>=previous_lower" in text
    assert "availability_time-decision_time)!=900" in text


def test_chandelier_is_completed_bar_only_and_tightens() -> None:
    text = source()
    assert "CopyBuffer(g_atr_handle,0,1,1,value)" in text
    assert "HighestHigh(rates,0,last)-CHANDELIER_ATR_MULTIPLIER*atr" in text
    assert "LowestLow(rates,0,last)+CHANDELIER_ATR_MULTIPLIER*atr" in text
    assert "next_stop<=old_stop+0.5*_Point" in text
    assert "next_stop>=old_stop-0.5*_Point" in text
    assert 'const bool crossed=(direction>0 ? tick.bid<=stop : tick.ask>=stop);' in text
    assert 'ClosePositionTicket(ticket,"DCX_CHANDELIER_CROSS")' in text


def test_no_target_no_optimization_and_no_lookahead_access() -> None:
    text = source()
    assert "request.tp=0.0" in text
    assert "CopyRates(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates)" in text
    assert "CopyRates(_Symbol,PERIOD_M15,0" not in text
    assert "CopyBuffer(g_atr_handle,0,0" not in text
    forbidden = ("Optimize", "InpDonchian", "InpAtrPeriod", "InpChandelier", "WebRequest")
    assert not any(token in text for token in forbidden)


def test_trade_gate_and_weekend_flatten_are_present() -> None:
    text = source()
    assert "!OwnedPositionCount(positions) || !OwnedOrderCount(orders)" in text
    assert "OWNED_INVENTORY_UNCERTAIN" in text
    assert "POSITION_ENUMERATION" in text and "POSITION_PROPERTIES" in text
    assert "CLOSE_POSITION_PROPERTIES" in text
    assert "TRAIL_POSITION_PROPERTIES" in text
    assert "g_runtime_failed=true;\n      PrintFormat(\"DCX001_CLOSE_REJECT" in text
    assert "!SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL,stops_level)" in text
    assert "!IsUsable(old_stop) || old_stop<0.0" in text
    assert "FOK_NOT_SUPPORTED" in text
    assert "return(ORDER_FILLING_FOK);" in text
    assert "p.day_of_week==0 ||" in text and "p.day_of_week==6" in text
    assert "p.day_of_week==5 && p.hour>=InpFridayFlattenHour" in text
    assert "now>=DESIGN_TO" in text


def test_prereg_has_sealed_splits_and_kill_rule() -> None:
    text = PREREG.read_text(encoding="utf-8")
    assert "2010-01-04" in text and "2018-01-01" in text
    assert "Validation: `[2018-01-01, 2021-01-01)` sealed" in text
    assert "Final holdout: `[2021-01-01, 2023-01-01)` sealed" in text
    assert "without session/direction/period/ATR/multiplier/risk/exit rescue" in text
