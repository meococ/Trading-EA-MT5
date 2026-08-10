from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_CCIExpansion.mq5"
PREREG = ROOT / "research" / "HYP-CCI-XAUUSD-M15-001_FROZEN_PREREG.md"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_frozen_identity_and_native_indicator():
    text = source()
    assert 'EXPECTED_SYMBOL="XAUUSD"' in text
    assert 'EXPECTED_HYPOTHESIS="HYP-CCI-XAUUSD-M15-001"' in text
    assert 'EXPECTED_VARIANT="CCI20_TYPICAL_100_EXPANSION"' in text
    assert 'InpMagic==5604201' in text
    assert 'iCCI(_Symbol,PERIOD_M15,CCI_PERIOD,PRICE_TYPICAL)' in text
    assert 'iATR(_Symbol,PERIOD_M15,ATR_PERIOD)' in text


def test_closed_bar_expansion_and_exact_next_clock():
    text = source()
    assert 'prior_cci=cci_values[0];' in text
    assert 'current_cci=cci_values[1];' in text
    assert 'CopyBuffer(g_cci_handle,0,1,2,cci_values)' in text
    assert 'prior_cci<=100.0 && current_cci>100.0' in text
    assert 'prior_cci>=-100.0 && current_cci<-100.0' in text
    assert '(long)(availability_time-decision_time)!=900' in text
    assert 'ProcessCciClosedBar(current_open,signal)' in text
    assert 'if(ProcessClosedBar(current_open,signal)' not in text


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
    assert 'ACCOUNT_MARGIN_SO_CALL' in text
    assert 'ACCOUNT_MARGIN_SO_SO' in text
    assert 'ACCOUNT_STOPOUT_MODE_MONEY' in text
    assert 'MARGIN_HEADROOM_RESERVE_FACTOR=0.20' in text
    assert 'MARGIN_FREE_EQUITY_FLOOR=0.01' in text
    assert 'allowed_new_margin/margin_one_lot' in text
    assert 'sized-step' in text
    for reason in (
        'TICK_SIZE_PROPERTY',
        'SYMBOL_TICK',
        'ORDER_CALC_PROFIT',
        'MARGIN_ACCOUNT_STATE',
        'VOLUME_PROPERTIES',
        'MARGIN_ONE_LOT',
        'MARGIN_EXACT',
        'STOPS_LEVEL_PROPERTY',
        'ORDER_CHECK',
    ):
        assert f'CCI001_FATAL reason={reason}' in text
    assert 'tick_size=_Point' not in text


def test_prereg_was_frozen_for_direct_baseline():
    text = PREREG.read_text(encoding='utf-8')
    assert 'Status: `FROZEN_BEFORE_SOURCE_AND_OUTCOMES`.' in text
    assert 'Exactly one untuned baseline' in text
    assert 'no source-only detour' in text
    assert 'Any material miss kills this exact mapping.' in text


def test_native_indicator_warmup_is_deferred_but_fail_closed():
    text = source()
    assert 'g_indicators_ready=PreloadCciState();' in text
    assert 'if(!g_indicators_ready)\n     {\n      g_indicators_ready=PreloadCciState();' in text
    assert 'if(!g_indicators_ready)\n      g_runtime_failed=true;' in text
    assert 'CCI001_FATAL reason=CCI_PRELOAD' not in text
    transition = text.index('g_indicators_ready=PreloadCciState();', text.index('void OnTick()'))
    reanchor = text.index('g_last_bar_open=warmup_open;', transition)
    transition_return = text.index('return;', reanchor)
    scheduler = text.index('datetime current_open=0;', transition)
    assert transition < reanchor < transition_return < scheduler


def test_active_path_has_no_stale_frama_identity():
    text = source()
    assert 'FRAMA' not in text
    assert 'iFrAMA' not in text
    assert '5604102' not in text
