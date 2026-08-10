from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "EA_FisherTrendPullback.mq5"
PREREG = ROOT / "research" / "HYP-FTP-XAUUSD-M15-001_FROZEN_PREREG.md"


def text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_and_closed_bar_contract() -> None:
    source = text()
    assert 'EXPECTED_HYPOTHESIS="HYP-FTP-XAUUSD-M15-001"' in source
    assert 'EXPECTED_VARIANT="FISHER10_EMA200_PULLBACK_V1"' in source
    assert "CopyRates(_Symbol,PERIOD_M15,1,FISHER_LENGTH" in source
    assert "CopyBuffer(g_atr_handle,0,1,1" in source
    assert "CopyBuffer(g_ema_handle,0,1,1" in source
    assert "CopyBuffer(g_ema_handle,0,9,1" in source


def test_exact_fisher_and_signal_boundaries() -> None:
    source = text()
    assert "0.33*raw+0.67*value_state" in source
    assert "0.5*MathLog((1.0+value_state)/(1.0-value_state))+0.5*fish_state" in source
    assert "prior_fish<=-FISHER_EXTREME && next_fish>prior_fish" in source
    assert "prior_fish>=FISHER_EXTREME && next_fish<prior_fish" in source
    assert "rates[current].close>ema && ema>prior_ema" in source
    assert "rates[current].close<ema && ema<prior_ema" in source


def test_frozen_lifecycle_and_risk() -> None:
    source = text()
    assert "STOP_ATR_FLOOR=1.25" in source
    assert "STOP_ATR_BUFFER=0.25" in source
    assert "TARGET_R=1.50" in source
    assert "MAX_HOLD_BARS=12" in source
    assert "ORDER_FILLING_FOK" in source
    assert "retcode==TRADE_RETCODE_DONE" in source
    assert "OrderCalcProfit" in source
    assert "OrderCalcMargin" in source
    assert "shift>=MAX_HOLD_BARS" in source


def test_no_posthoc_filters_or_trailing() -> None:
    source = text().lower()
    for forbidden in ("sessionstart", "sessionend", "newsfilter", "weekdayfilter", "trailingstop", "breakeven"):
        assert forbidden not in source


def test_prereg_freezes_train_and_sealed_splits() -> None:
    prereg = PREREG.read_text(encoding="utf-8")
    assert "2010-01-04" in prereg
    assert "2018-01-01" in prereg
    assert "2021-01-01" in prereg
    assert "2023-01-01" in prereg
    assert "PF strictly greater than 1.30" in prereg
    assert "2.0–5.0" in prereg
