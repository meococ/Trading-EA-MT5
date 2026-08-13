from pathlib import Path


SOURCE = Path(__file__).parents[1] / "EA_PriorDayAcceptanceContinuation.mq5"


def text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_closed_h1_and_exact_next() -> None:
    source = text()
    assert "CopyRates(_Symbol,PERIOD_H1,1,REQUIRED_RATES,rates)" in source
    assert "availability_time-decision_time!=3600" in source
    assert "_Period!=PERIOD_H1" in source


def test_exact_two_close_acceptance_predicates() -> None:
    source = text()
    assert "c2<=prior_high && c1>prior_high" in source
    assert "c0>prior_high && c0>c1" in source
    assert "c2>=prior_low && c1<prior_low" in source
    assert "c0<prior_low && c0<c1" in source
    assert "first_event_index!=last" in source


def test_frozen_geometry_and_risk() -> None:
    source = text()
    assert "STOP_INSIDE_PRIOR_RANGE=0.25" in source
    assert "TARGET_R=1.50" in source
    assert "MAX_HOLD_BARS=8" in source
    assert "InpRiskPercent=0.25" in source
    assert "OrderCalcProfit" in source


def test_no_bar_zero_signal_or_pending_orders() -> None:
    source = text()
    assert "CopyRates(_Symbol,PERIOD_H1,0" not in source
    assert "CopyBuffer" not in source
    assert "OrderSendAsync" not in source
    assert "BuyLimit" not in source and "SellLimit" not in source


def test_d0_proof_is_read_only() -> None:
    source = text()
    assert "DATA_EPOCH_D0_SERIES_PROOF" in source
    assert "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)" in source


def test_pre_mt5_alignment_and_attach_fail_closed() -> None:
    source = text()
    assert 'EXPECTED_HYPOTHESIS="HYP-PDAC-XAUUSD-H1-002"' in source
    assert "p.day_of_week==5 && p.hour>=InpFridayFlattenHourUtc" in source
    assert "g_last_bar_open=attach_bar_open" in source
