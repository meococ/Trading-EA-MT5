from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "03. EA Developer/EA_ATRImpulsePullbackContinuation/EA_ATRImpulsePullbackContinuation.mq5"
PREREG = ROOT / "03. EA Developer/EA_ATRImpulsePullbackContinuation/research/HYP-APC-XAUUSD-M15-002_FROZEN_PREREG.md"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_fresh_identity_and_unchanged_economic_parameters() -> None:
    text = source()
    for token in (
        'EXPECTED_HYPOTHESIS="HYP-APC-XAUUSD-M15-002"',
        'EXPECTED_VARIANT="ATR14_EMA50_ADX14_IMPULSE_PULLBACK_RELEASE_V2_D0_FLATSAFE"',
        'InpMagic=5603902', 'IMPULSE_TR_ATR=1.35', 'IMPULSE_BODY_FRAC=0.55',
        'IMPULSE_CLOSE_LOCATION=0.70', 'PULLBACK_TR_ATR=0.85',
        'RELEASE_MAX_EXTENSION_ATR=0.35', 'STOP_BUFFER_ATR=0.20',
        'TARGET_R=1.45', 'MAX_HOLD_BARS=10',
        "DESIGN_FROM=D'2010.01.04 00:00'", "DESIGN_TO=D'2018.01.01 00:00'",
    ):
        assert token in text


def test_d0_series_proof_is_exact_and_nondecision_only() -> None:
    text = source()
    for token in (
        'SeriesInfoInteger(_Symbol,timeframe,property,value)',
        'PERIOD_M5,SERIES_SYNCHRONIZED', 'PERIOD_M5,SERIES_FIRSTDATE',
        'PERIOD_M5,SERIES_TERMINAL_FIRSTDATE', 'PERIOD_M1,SERIES_SERVER_FIRSTDATE',
        'PERIOD_M1,SERIES_TERMINAL_FIRSTDATE', 'PERIOD_M5,SERIES_BARS_COUNT',
        'CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)',
        'DATA_EPOCH_D0_SERIES_PROOF symbol=%s', 'if(!EmitD0SeriesProof())',
        'copytime_result!=1 ||',
        'copytime_first_epoch!=m5_first_epoch || copytime_error!=0',
    ):
        assert token in text
    assert text.index('if(!EmitD0SeriesProof())') < text.index('g_atr_handle=iATR')


def test_flat_impulse_is_consumed_before_division_without_runtime_failure() -> None:
    text = source()
    guard = text.index('if(impulse_tr==0.0)')
    division = text.index('const double long_close_location=')
    assert guard < division
    block = text[guard:division]
    assert 'return(false);' in block
    assert 'g_runtime_failed=true' not in block
    fatal = text[text.index('if(!IsUsable(impulse_tr)'):guard]
    assert 'g_runtime_failed=true;' in fatal


def test_closed_bar_signal_and_execution_contract_remain_frozen() -> None:
    text = source()
    for token in (
        'CopyRates(_Symbol,PERIOD_M15,1,REQUIRED_RATES,rates)',
        'ReadIndicator(g_atr_handle,0,1,atr_release)',
        'ReadIndicator(g_ema_handle,0,9,ema_slope_ref)',
        'ReadIndicator(g_adx_handle,0,4,adx_rise_ref)',
        'availability_time-decision_time)!=900',
        'entry+TARGET_R*risk : entry-TARGET_R*risk',
        'shift>=MAX_HOLD_BARS',
        'OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit)',
        'return(retcode==TRADE_RETCODE_DONE);',
    ):
        assert token in text
    assert 'CopyRates(_Symbol,PERIOD_M15,0' not in text


def test_prereg_closes_parent_without_outcome_informed_rescue() -> None:
    text = PREREG.read_text(encoding="utf-8")
    assert 'opened no admissible economics' in text
    assert 'Engineering changes only' in text
    assert 'without threshold/session/direction/stop/target/hold/risk rescue' in text
