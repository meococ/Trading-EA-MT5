from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_DeMarkerReentry.mq5"
PREREG = ROOT / "research" / "HYP-DMR-XAUUSD-M15-002_FROZEN_PREREG.md"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_frozen_identity_and_native_indicator():
    text = source()
    assert 'EXPECTED_SYMBOL="XAUUSD"' in text
    assert 'EXPECTED_HYPOTHESIS="HYP-DMR-XAUUSD-M15-002"' in text
    assert 'EXPECTED_VARIANT="DEMARKER14_030_070_REENTRY_BROKER_VALID_GEOMETRY"' in text
    assert 'InpMagic==5604302' in text
    assert 'DEMARKER_PERIOD=14' in text
    assert 'iDeMarker(_Symbol,PERIOD_M15,DEMARKER_PERIOD)' in text
    assert 'iATR(_Symbol,PERIOD_M15,ATR_PERIOD)' in text


def test_closed_bar_reentry_and_exact_next_clock():
    text = source()
    assert 'prior_demarker=demarker_values[0];' in text
    assert 'current_demarker=demarker_values[1];' in text
    assert 'CopyBuffer(g_demarker_handle,0,1,2,demarker_values)' in text
    assert 'prior_demarker<=0.30 && current_demarker>0.30' in text
    assert 'prior_demarker>=0.70 && current_demarker<0.70' in text
    assert '(long)(availability_time-decision_time)!=900' in text
    assert 'ProcessDeMarkerClosedBar(current_open,signal)' in text
    assert 'if(ProcessClosedBar(current_open,signal)' not in text


def test_frozen_exit_geometry_and_window():
    text = source()
    assert 'STOP_BUFFER_ATR=0.20' in text
    assert 'TARGET_R=1.50' in text
    assert 'MAX_HOLD_BARS=12' in text
    assert 'REQUIRED_RATES=5' in text
    assert "DESIGN_FROM=D'2018.01.01 00:00'" in text
    assert "DESIGN_TO=D'2023.01.01 00:00'" in text


def test_broker_reference_geometry_rejects_without_moving_levels():
    text = source()
    assert '(signal.direction>0 ? tick.bid-stop : stop-tick.ask)' in text
    assert '(signal.direction>0 ? target-tick.bid : tick.ask-target)' in text
    assert 'stop_reference_distance+1e-12<minimum_distance' in text
    assert 'target_reference_distance+1e-12<minimum_distance' in text
    assert 'g_geometry_rejects++' in text
    assert 'geometry_rejects=%I64d' in text
    assert 'request.sl=stop;' in text
    assert 'request.tp=target;' in text
    assert 'minimum_distance' not in text[text.index('request.sl=stop;'):text.index('request.tp=target;')]


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
        'TICK_SIZE_PROPERTY', 'SYMBOL_TICK', 'ORDER_CALC_PROFIT',
        'MARGIN_ACCOUNT_STATE', 'VOLUME_PROPERTIES', 'MARGIN_ONE_LOT',
        'MARGIN_EXACT', 'STOPS_LEVEL_PROPERTY', 'ORDER_CHECK',
    ):
        assert f'DMR002_FATAL reason={reason}' in text
    assert 'tick_size=_Point' not in text


def test_prereg_freezes_only_the_broker_geometry_revision():
    text = PREREG.read_text(encoding='utf-8')
    assert 'Frozen before source revision, compile, or outcome access' in text
    assert 'Do not move, widen, clamp, or retry SL/TP.' in text
    assert 'PF `>1.30` after costs' in text


def test_native_indicator_warmup_is_deferred_but_fail_closed():
    text = source()
    assert 'g_indicators_ready=PreloadDeMarkerState();' in text
    assert 'if(!g_indicators_ready)\n     {\n      g_indicators_ready=PreloadDeMarkerState();' in text
    assert 'if(!g_indicators_ready)\n      g_runtime_failed=true;' in text
    transition = text.index('g_indicators_ready=PreloadDeMarkerState();', text.index('void OnTick()'))
    reanchor = text.index('g_last_bar_open=warmup_open;', transition)
    transition_return = text.index('return;', reanchor)
    scheduler = text.index('datetime current_open=0;', transition)
    assert transition < reanchor < transition_return < scheduler


def test_active_path_has_no_stale_cci_identity():
    text = source()
    for stale in ('EA_CCIExpansion', 'HYP-CCI-XAUUSD-M15-001',
                  'CCI20_TYPICAL_100_EXPANSION', '5604201', 'iCCI('):
        assert stale not in text
