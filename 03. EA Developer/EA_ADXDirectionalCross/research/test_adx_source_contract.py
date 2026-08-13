from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_ADXDirectionalCross.mq5"
PREREG = ROOT / "research" / "HYP-ADX-XAUUSD-M15-001_FROZEN_PREREG.md"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_frozen_identity_and_native_handles():
    text = source()
    assert 'EA_NAME="EA_ADXDirectionalCross"' in text
    assert 'EXPECTED_HYPOTHESIS="HYP-ADX-XAUUSD-M15-001"' in text
    assert 'EXPECTED_VARIANT="ADX14_DI_CROSS_STRENGTH25_RISING"' in text
    assert 'InpMagic==5604401' in text
    assert 'iADX(_Symbol,PERIOD_M15,ADX_PERIOD)' in text
    assert 'iATR(_Symbol,PERIOD_M15,ATR_PERIOD)' in text


def test_closed_bar_di_cross_and_strength_gate():
    text = source()
    assert 'CopyBuffer(g_adx_handle,0,1,2,adx_values)' in text
    assert 'CopyBuffer(g_adx_handle,1,1,2,plus_values)' in text
    assert 'CopyBuffer(g_adx_handle,2,1,2,minus_values)' in text
    assert 'prior_plus<=prior_minus && current_plus>current_minus' in text
    assert 'prior_plus>=prior_minus && current_plus<current_minus' in text
    assert 'current_adx>=25.0 && current_adx>prior_adx' in text


def test_exact_next_clock_and_design_window():
    text = source()
    assert '(long)(availability_time-decision_time)!=900' in text
    assert 'ProcessAdxClosedBar(current_open,signal)' in text
    assert "DESIGN_FROM=D'2018.01.01 00:00'" in text
    assert "DESIGN_TO=D'2023.01.01 00:00'" in text


def test_frozen_exit_and_risk_contract():
    text = source()
    for token in ('STOP_BUFFER_ATR=0.20', 'TARGET_R=1.50',
                  'MAX_HOLD_BARS=12', 'REQUIRED_RATES=5'):
        assert token in text
    assert 'InpMaxTradesPerDay==1' in text
    assert 'MathAbs(InpRiskPercent-0.25)<1e-12' in text


def test_broker_reference_geometry_is_fail_closed():
    text = source()
    assert '(signal.direction>0 ? tick.bid-stop : stop-tick.ask)' in text
    assert '(signal.direction>0 ? target-tick.bid : tick.ask-target)' in text
    assert 'g_geometry_rejects++' in text
    assert 'request.sl=stop;' in text and 'request.tp=target;' in text


def test_runtime_summary_and_ordercheck_are_auditable():
    text = source()
    assert 'ADX001_SUMMARY' in text
    assert 'geometry_rejects=%I64d' in text
    assert 'ADX001_FATAL reason=ORDER_CHECK' in text
    assert 'stop_distance=%.8f target_distance=%.8f minimum_distance=%.8f' in text


def test_prereg_blocks_posthoc_rescue_and_holdout():
    text = PREREG.read_text(encoding="utf-8")
    assert 'FROZEN_BEFORE_SOURCE_AND_OUTCOMES' in text
    assert 'PF `>1.30` after costs' in text
    assert 'no post-hoc threshold/period/filter/session/SL-TP/daily-cap rescue' in text


def test_active_source_has_no_demarker_identity():
    text = source()
    for stale in ('iDeMarker(', 'HYP-DMR-', 'DMR001', 'DMR002',
                  'DEMARKER14_030_070_REENTRY', 'EA_DeMarkerReentry'):
        assert stale not in text
