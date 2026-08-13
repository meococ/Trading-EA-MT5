from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "EA_EuropeInitialBalanceBreakout.mq5"
PREREG = ROOT / "research/HYP-EIBB-XAUUSD-M15-001_FROZEN_ECONOMIC_PREREG.md"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_and_frozen_inputs() -> None:
    text = source_text()
    assert 'EXPECTED_HYPOTHESIS="HYP-EIBB-XAUUSD-M15-001"' in text
    assert 'EXPECTED_VARIANT="UTC0700_4BAR_INITIAL_BALANCE_FIRST_CLOSE_BREAK"' in text
    assert "InpMagic!=5604501" in text
    assert "MathAbs(InpRiskPercent-0.10)>1e-12" in text


def test_runtime_reconstructs_m15_from_native_m5() -> None:
    text = source_text()
    assert "CopyRates(_Symbol,PERIOD_M5,1,HISTORY_BARS,rates)" in text
    assert "BuildSyntheticM15" in text
    assert "utc1-utc0)!=300" in text
    assert "utc2-utc1)!=300" in text
    assert "MinuteOfDay(utc0)%15!=0" in text
    assert "CopyRates(_Symbol,PERIOD_M15" not in text


def test_signal_uses_exact_initial_balance_and_first_break() -> None:
    text = source_text()
    assert "INITIAL_BALANCE_START_MINUTE_UTC=7*60" in text
    assert "INITIAL_BALANCE_BARS=4" in text
    assert "SCAN_START_MINUTE_UTC=8*60" in text
    assert "SCAN_END_MINUTE_UTC=16*60" in text
    assert "bars[i].close>ib_high" in text
    assert "bars[i].close<ib_low" in text
    assert "first_break_time!=decision_time" in text
    assert "g_consumed_utc_date" in text


def test_closed_bar_and_exact_next_only() -> None:
    text = source_text()
    assert "CopyRates(_Symbol,PERIOD_M5,1,HISTORY_BARS,rates)" in text
    assert "availability_time-decision_time)!=900" in text
    assert "availability_utc-decision_utc)!=900" in text
    assert "CopyRates(_Symbol,PERIOD_M5,0" not in text


def test_frozen_stop_target_and_hold() -> None:
    text = source_text()
    assert "signal.structural_stop=(first_direction>0 ? ib_low : ib_high)" in text
    assert "const double TARGET_R=1.50" in text
    assert "const int MAX_HOLD_M5_BARS=48" in text
    assert "shift>=MAX_HOLD_M5_BARS" in text
    assert "InpSessionFlattenHourUtc!=20" in text


def test_summary_explains_source_to_trade_funnel() -> None:
    text = source_text()
    for token in (
        "ib_dates=%I64d", "raw=%I64d", "entries=%I64d", "rejects=%I64d",
        "close_attempts=%I64d", "close_rejects=%I64d", "risk_lock_skips=%I64d",
    ):
        assert token in text


def test_no_parameter_rescue_was_added() -> None:
    text = source_text().lower()
    for forbidden in ("inpminrange", "inpweekday", "inptrendfilter", "inpvolume", "inpcooldown"):
        assert forbidden not in text
    prereg = PREREG.read_text(encoding="utf-8")
    assert "No session, range-size, direction, weekday, stop/target, risk or hold change" in prereg

