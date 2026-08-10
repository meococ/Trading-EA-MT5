from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "03. EA Developer/EA_ATRImpulsePullbackContinuation/EA_ATRImpulsePullbackContinuation.mq5"
PREREG = ROOT / "03. EA Developer/EA_ATRImpulsePullbackContinuation/research/HYP-APC-XAUUSD-M15-001_FROZEN_PREREG.md"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_and_frozen_parameters() -> None:
    text = source()
    for token in (
        'EXPECTED_HYPOTHESIS="HYP-APC-XAUUSD-M15-001"',
        'EXPECTED_VARIANT="ATR14_EMA50_ADX14_IMPULSE_PULLBACK_RELEASE_V1"',
        'EXPECTED_SYMBOL="XAUUSD"',
        "ATR_PERIOD=14", "EMA_PERIOD=50", "ADX_PERIOD=14",
        "MIN_ADX=18.0", "IMPULSE_TR_ATR=1.35", "IMPULSE_BODY_FRAC=0.55",
        "IMPULSE_CLOSE_LOCATION=0.70", "PULLBACK_TR_ATR=0.85",
        "RELEASE_MAX_EXTENSION_ATR=0.35", "STOP_BUFFER_ATR=0.20",
        "TARGET_R=1.45", "MAX_HOLD_BARS=10", "InpMagic=5603901",
        "DESIGN_FROM=D'2010.01.04 00:00'", "DESIGN_TO=D'2018.01.01 00:00'",
    ):
        assert token in text


def test_exact_three_bar_signal_and_closed_indicator_shifts() -> None:
    text = source()
    for token in (
        "const int release=ArraySize(rates)-1",
        "const int pullback=release-1",
        "const int impulse=release-2",
        "ReadIndicator(g_atr_handle,0,1,atr_release)",
        "ReadIndicator(g_atr_handle,0,2,atr_pullback)",
        "ReadIndicator(g_atr_handle,0,3,atr_impulse)",
        "ReadIndicator(g_ema_handle,0,1,ema_release)",
        "ReadIndicator(g_ema_handle,0,9,ema_slope_ref)",
        "ReadIndicator(g_adx_handle,0,1,adx_release)",
        "ReadIndicator(g_adx_handle,0,4,adx_rise_ref)",
        "ReadIndicator(g_adx_handle,1,1,plus_di)",
        "ReadIndicator(g_adx_handle,2,1,minus_di)",
        "availability_time-decision_time)!=900",
    ):
        assert token in text
    assert "CopyRates(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates)" in text
    assert "CopyRates(_Symbol,PERIOD_M15,0" not in text
    assert "CopyBuffer(g_atr_handle,0,0" not in text
    assert "CopyBuffer(g_ema_handle,0,0" not in text
    assert "CopyBuffer(g_adx_handle,0,0" not in text


def test_frozen_predicates_are_literal() -> None:
    text = source()
    for token in (
        "impulse_tr>=IMPULSE_TR_ATR*atr_impulse",
        "impulse_body>=IMPULSE_BODY_FRAC*impulse_tr",
        "long_close_location>=IMPULSE_CLOSE_LOCATION",
        "pullback_tr<=PULLBACK_TR_ATR*atr_pullback",
        "rates[pullback].low>=impulse_mid",
        "rates[pullback].close>=rates[impulse].open",
        "rates[release].close>rates[pullback].high",
        "rates[release].close<=rates[impulse].high+RELEASE_MAX_EXTENSION_ATR*atr_release",
        "ema_release>ema_slope_ref", "adx_release>adx_rise_ref", "plus_di>minus_di",
        "ema_release<ema_slope_ref", "minus_di>plus_di",
    ):
        assert token in text


def test_stop_target_time_exit_and_one_signal_day() -> None:
    text = source()
    assert "MathMin(rates[impulse].low,rates[pullback].low)-STOP_BUFFER_ATR*atr_release" in text
    assert "MathMax(rates[impulse].high,rates[pullback].high)+STOP_BUFFER_ATR*atr_release" in text
    assert "entry+TARGET_R*risk : entry-TARGET_R*risk" in text
    assert "target=(signal.direction>0 ? FloorToTick(target) : CeilToTick(target))" in text
    assert "shift>=MAX_HOLD_BARS" in text
    assert 'ClosePositionTicket(ticket,"APC_TIME_EXIT")' in text
    assert "date_key==g_consumed_signal_date" in text
    assert "g_consumed_signal_date=date_key" in text
    assert "InpMaxTradesPerDay==1" in text


def test_risk_and_inventory_are_fail_closed() -> None:
    text = source()
    for token in (
        "OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit)",
        "OrderCalcMargin(order_type,_Symbol,sized,entry,required_margin)",
        "!OwnedPositionCount(positions) || !OwnedOrderCount(orders)",
        "OWNED_INVENTORY_UNCERTAIN", "FOK_NOT_SUPPORTED",
        "p.day_of_week==5 && p.hour>=InpFridayFlattenHour",
        "now>=DESIGN_TO",
    ):
        assert token in text
    assert "return(retcode==TRADE_RETCODE_DONE);" in text
    assert "APC001_FATAL reason=CLOSED_RATE_LOAD" in text
    assert "APC001_FATAL reason=CLOSED_INDICATOR_LOAD" in text
    assert "APC001_FATAL reason=TRUE_RANGE_INVALID" in text
    assert "APC001_FATAL reason=M15_SCHEDULING_CLOCK" in text


def test_attempted_ambiguous_send_latches_runtime_failure() -> None:
    text = source()
    send_branch = text.split("if(!OrderSend(request,result) || !AcceptedRetcode(result.retcode))", 2)[2]
    assert "g_runtime_failed=true;" in send_branch.split("return(false);", 1)[0]
    assert "APC001_ORDER_SEND_REJECT" in send_branch.split("return(false);", 1)[0]


def test_prereg_seals_splits_and_kill_rule() -> None:
    text = PREREG.read_text(encoding="utf-8")
    assert "2010-01-04" in text and "2018-01-01" in text
    assert "Validation: `[2018-01-01, 2021-01-01)` sealed" in text
    assert "Final holdout: `[2021-01-01, 2023-01-01)` sealed" in text
    assert "without session/direction/threshold/period/stop/target/hold/risk rescue" in text
