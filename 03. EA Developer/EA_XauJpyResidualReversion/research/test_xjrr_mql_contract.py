from pathlib import Path
import re


SOURCE = Path(__file__).parents[1] / "EA_XauJpyResidualReversion.mq5"
TEXT = SOURCE.read_text(encoding="utf-8")


def test_identity_and_m5_chart_are_frozen() -> None:
    assert 'EXPECTED_HYPOTHESIS="HYP-XJRR-XAUUSD-M5-001"' in TEXT
    assert 'AUX_SYMBOL="USDJPY"' in TEXT
    assert "_Period!=PERIOD_M5" in TEXT
    assert "InpMagic!=5604501" in TEXT


def test_closed_pair_and_prior_window_contract() -> None:
    assert "CopyRates(symbol,PERIOD_M5,1,count,rates)" in TEXT
    assert "CopyRates(_Symbol,PERIOD_M5,1,64,xau)" in TEXT
    assert "CopyRates(AUX_SYMBOL,PERIOD_M5,1,64,jpy)" in TEXT
    assert "const int WINDOW=288" in TEXT
    assert "for(int k=index-WINDOW;k<=index-1;k++)" in TEXT
    assert "ComputeZAt(index-1" in TEXT and "ComputeZAt(index,beta" in TEXT


def test_daily_consumption_precedes_execution_filters() -> None:
    consume = TEXT.index("g_consumed_date=date_key;")
    exact_next = TEXT.index("const bool exact_next=", consume)
    friday = TEXT.index("if(FridayBlocked(current_open))", exact_next)
    overlap = TEXT.index("if(position_at_tick_start", friday)
    assert consume < exact_next < friday < overlap
    assert "g_lockout_remaining=LOCKOUT_BARS" in TEXT


def test_frozen_exit_stop_and_risk() -> None:
    assert "const double STOP_ATR=1.25" in TEXT
    assert "const int MAX_HOLD_BARS=12" in TEXT
    assert "current_z>=0.0" in TEXT and "current_z<=0.0" in TEXT
    assert "InpRiskPercent=0.25" in TEXT
    assert "PositionClose" in TEXT
    assert "iBarShift(_Symbol,PERIOD_M5,entry_time,false)" in TEXT
    assert "entry_time,true" not in TEXT


def test_no_bar_zero_signal_or_future_price_read() -> None:
    assert "CopyBuffer(g_atr_handle,0,1,1" in TEXT
    assert not re.search(r"CopyBuffer\([^\n]*,0,1,values", TEXT)
    assert "POSITION_TIME" in TEXT
    assert "next_close" not in TEXT.lower()


def test_summary_is_compact_and_classifies_population_loss() -> None:
    assert TEXT.count("XJRR_SUMMARY") == 1
    for field in ("consumed", "entries", "exact_next_rejects", "overlap_rejects", "friday_rejects", "geometry_rejects", "risk_lock_rejects", "runtime_rejects", "reconstructed_consumed"):
        assert field in TEXT
