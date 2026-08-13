from pathlib import Path

SRC = Path(__file__).parents[1] / "EA_OnlineRidge_EUR_H1_V12ML.mq5"
TEXT = SRC.read_text(encoding="utf-8")


def test_identity_and_binding():
    assert 'EXPECTED_HYPOTHESIS="HYP-ORLS-EURUSD-H1-001"' in TEXT
    assert '_Symbol!="EURUSD"||_Period!=PERIOD_H1' in TEXT


def test_closed_bar_features():
    assert 'CopyRates(_Symbol,PERIOD_H1,0,need,r)' in TEXT
    assert 'raw[0]=(r[1].close-r[2].close)' in TEXT
    assert 'raw[1]=(r[1].close-r[5].close)' in TEXT


def test_delayed_label_is_open_to_open():
    assert 'LABEL_HORIZON 4' in TEXT
    assert 'MathLog(current_open/g_sample_open[slot])' in TEXT
    assert 'now-g_sample_time[slot]==LABEL_HORIZON*PeriodSeconds(PERIOD_H1)' in TEXT


def test_prediction_uses_past_standardizer():
    assert TEXT.index('StandardizePastOnly(raw,z)') < TEXT.index('UpdateStandardizer(raw)')
    assert 'g_sample_z[slot][i]=z[i]' in TEXT


def test_rls_update_is_causal_and_fixed():
    assert 'den=InpForgettingFactor' in TEXT
    assert 'g_p[i][j]=(g_p[i][j]-gain[i]*row[j])/InpForgettingFactor' in TEXT
    assert 'InpForgettingFactor-.9975' in TEXT


def test_symmetric_cost_hurdle():
    assert 'spread_return+InpCommissionReturn+InpSlippageReturn' in TEXT
    assert 'score>hurdle' in TEXT and 'score<-hurdle' in TEXT


def test_fixed_horizon_and_catastrophe_stop():
    assert 'reason="FIXED_HORIZON"' in TEXT
    assert 'InpSLATRMult*s.atr14' in TEXT
    assert 'InpSLMinPips*pip' in TEXT and 'InpSLMaxPips*pip' in TEXT


def test_no_rescue_exit_family():
    assert 'BREAKEVEN' not in TEXT
    assert 'TRAIL' not in TEXT
    assert 'PositionOpen(_Symbol,type,volume,entry,sl,0.0' in TEXT


def test_canonical_series_proof_and_summary():
    assert 'DATA_EPOCH_D0_SERIES_PROOF' in TEXT
    assert 'runtime_failed=%s' in TEXT
    assert 'rls_updates=%I64d' in TEXT
