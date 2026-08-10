from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_FRAMAAdaptiveFlip.mq5"
PREREG = ROOT / "research" / "HYP-FRAMA-XAUUSD-M15-002_FROZEN_PREREG.md"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_frozen_identity_and_native_indicator():
    text = source()
    assert 'EXPECTED_SYMBOL="XAUUSD"' in text
    assert 'EXPECTED_HYPOTHESIS="HYP-FRAMA-XAUUSD-M15-002"' in text
    assert 'EXPECTED_VARIANT="FRAMA16_PRICE_CROSS_ADAPTIVE_FLIP_DEFERRED_WARMUP"' in text
    assert 'InpMagic==5604102' in text
    assert 'iFrAMA(_Symbol,PERIOD_M15,FRAMA_PERIOD,0,PRICE_CLOSE)' in text
    assert 'iATR(_Symbol,PERIOD_M15,ATR_PERIOD)' in text


def test_closed_bar_crossover_and_exact_next_clock():
    text = source()
    assert "bar_open=(datetime)raw;\n   return(true);" in text
    assert 'rates[prior].close<=prior_frama && rates[release].close>current_frama' in text
    assert 'rates[prior].close>=prior_frama && rates[release].close<current_frama' in text
    assert 'CopyBuffer(g_frama_handle,0,1,2,frama_values)' in text
    assert '(long)(availability_time-decision_time)!=900' in text
    assert 'ProcessFramaClosedBar(current_open,signal)' in text
    assert 'if(ProcessClosedBar(current_open,signal)' not in text
    assert 'PreloadFramaState()' in text
    assert 'if(!PreloadKvoState())' not in text


def test_frozen_exit_geometry_and_window():
    text = source()
    assert 'STOP_BUFFER_ATR=0.20' in text
    assert 'TARGET_R=1.50' in text
    assert 'MAX_HOLD_BARS=12' in text
    assert 'REQUIRED_RATES=5' in text
    assert "DESIGN_FROM=D'2018.01.01 00:00'" in text
    assert "DESIGN_TO=D'2023.01.01 00:00'" in text


def test_money_stopout_sizing_and_api_fail_closed():
    text = source()
    assert "ACCOUNT_MARGIN_SO_CALL" in text
    assert "ACCOUNT_MARGIN_SO_SO" in text
    assert "ACCOUNT_STOPOUT_MODE_MONEY" in text
    assert "MARGIN_HEADROOM_RESERVE_FACTOR=0.20" in text
    assert "MARGIN_FREE_EQUITY_FLOOR=0.01" in text
    assert "allowed_new_margin/margin_one_lot" in text
    assert "sized-step" in text
    for reason in (
        "TICK_SIZE_PROPERTY",
        "SYMBOL_TICK",
        "ORDER_CALC_PROFIT",
        "MARGIN_ACCOUNT_STATE",
        "VOLUME_PROPERTIES",
        "MARGIN_ONE_LOT",
        "MARGIN_EXACT",
        "STOPS_LEVEL_PROPERTY",
        "ORDER_CHECK",
    ):
        assert f"FRAMA001_FATAL reason={reason}" in text
    assert "tick_size=_Point" not in text


def test_prereg_was_frozen_for_direct_baseline():
    text = PREREG.read_text(encoding="utf-8")
    assert "Status: `FROZEN_BEFORE_REVISION_SOURCE_AND_OUTCOMES`." in text
    assert "No signal, stop, target, sizing, filter" in text
    assert "Exactly one untuned Model-0 baseline" in text


def test_native_indicator_warmup_is_deferred_but_fail_closed():
    text = source()
    assert "g_indicators_ready=PreloadFramaState();" in text
    assert "if(!g_indicators_ready)\n     {\n      g_indicators_ready=PreloadFramaState();" in text
    assert "if(!g_indicators_ready)\n      g_runtime_failed=true;" in text
    assert "FRAMA001_FATAL reason=FRAMA_PRELOAD" not in text
    transition = text.index("g_indicators_ready=PreloadFramaState();", text.index("void OnTick()"))
    reanchor = text.index("g_last_bar_open=warmup_open;", transition)
    transition_return = text.index("return;", reanchor)
    scheduler = text.index("datetime current_open=0;", transition)
    assert transition < reanchor < transition_return < scheduler
