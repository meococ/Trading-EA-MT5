import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "03. EA Developer" / "EA_JCDR_PureReversal"
SOURCE = PACKAGE / "EA_JCDR_PureReversal.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
PREREG = PACKAGE / "research" / "HYP-JCDR-EURUSD-M5-006_FROZEN_PREREG.md"
COMPILE_LOG = PACKAGE / "EA_JCDR_PureReversal.log"
EX5 = PACKAGE / "EA_JCDR_PureReversal.ex5"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_identity_is_fresh_and_single_mechanism() -> None:
    text = source()
    assert 'EXPECTED_HYPOTHESIS="HYP-JCDR-EURUSD-M5-006"' in text
    assert 'EXPECTED_VARIANT="JCDR_PURE_REVERSAL_V1"' in text
    assert 'EXPECTED_SYMBOL="EURUSD"' in text
    for forbidden in ("iCustom(", "CopyBuffer(", "AI_Regime", "QQE", "Bollinger", "Smart_Money"):
        assert forbidden not in text


def test_exact_source_parameters_and_inclusive_boundaries() -> None:
    text = source()
    expected = {
        "JCDR_SCALE_RETURNS": "48",
        "JCDR_CLUSTER_BARS": "15",
        "JCDR_MIN_JUMPS": "3",
        "JCDR_MIN_COHERENCE": "0.80",
        "JCDR_MIN_DISPLACEMENT_PIP": "4.0",
        "JCDR_JUMP_FLOOR_PIP": "1.20",
        "JCDR_JUMP_MULTIPLIER": "3.0",
        "JCDR_DECAY_MAX_BARS": "10",
        "JCDR_RETRACE_MIN": "0.25",
        "JCDR_RETRACE_MAX": "1.00",
    }
    for name, value in expected.items():
        assert re.search(rf"const (?:int|double)\s+{name}\s*=\s*{re.escape(value)};", text)
    assert "MathAbs(bar.ret_pips)>=bar.jump_threshold_pips" in text
    assert "if(coherence<JCDR_MIN_COHERENCE)" in text
    assert "if(signed_displacement<JCDR_MIN_DISPLACEMENT_PIP)" in text
    assert "retracement<JCDR_RETRACE_MIN" in text
    assert "retracement>JCDR_RETRACE_MAX" in text


def test_closed_bar_clock_and_gap_fail_closed() -> None:
    text = source()
    assert "iTime(_Symbol,PERIOD_M5,1)" in text
    for field in ("iOpen", "iHigh", "iLow", "iClose"):
        assert f"{field}(_Symbol,PERIOD_M5,1)" in text
        assert f"{field}(_Symbol,PERIOD_M5,0)" not in text
    assert "(long)(bar.time-g_last_processed_time)!=300" in text
    assert "ResetFormation();" in text
    assert "current_open==g_last_bar_open" in text


def test_cluster_replacement_precedes_decay_and_emits_no_same_bar_signal() -> None:
    text = source()
    form = text.index("if(TryFormCluster(new_cluster))")
    pending = text.index("if(!g_pending.active)", form)
    block = text[form:pending]
    assert "g_pending=new_cluster;" in block
    assert "return(false);" in block


def test_direction_stop_target_and_time_exit_are_frozen() -> None:
    text = source()
    assert "signal.direction=-g_pending.dominant_sign;" in text
    assert "MathMax(JCDR_MIN_STOP_PIP" in text
    assert "JCDR_STOP_BUFFER_PIP" in text
    assert "const double JCDR_TARGET_R=1.50;" in text
    assert "entry+JCDR_TARGET_R*risk" in text
    assert "entry-JCDR_TARGET_R*risk" in text
    assert "held_bars>=InpMaxHoldBars" in text
    assert "InpMaxHoldBars==12" in text


def test_one_decision_per_server_day_and_no_session_filter() -> None:
    text = source()
    assert "const int date_key=DateKey(bar.time);" in text
    assert "date_key==g_consumed_signal_date" in text
    assert "g_consumed_signal_date=date_key;" in text
    for forbidden in ("TradeStart", "TradeEnd", "AsianStart", "London", "NewYork"):
        assert forbidden not in text


def test_design_and_weekend_boundaries_are_exact() -> None:
    text = source()
    assert "const datetime DESIGN_FROM=D'2016.01.04 00:00';" in text
    assert "const datetime DESIGN_TO=D'2021.01.01 00:00';" in text
    assert "bar_time<DESIGN_FROM || bar_time>=DESIGN_TO || availability_time>=DESIGN_TO" in text
    assert "p.day_of_week==5 && p.hour>=InpFridayFlattenHour" in text
    assert "InpFridayFlattenHour==20" in text


def test_risk_sizing_and_order_checks_are_fail_closed() -> None:
    text = source()
    assert "OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot_profit)" in text
    assert "equity*InpRiskPercent/100.0" in text
    assert "MathFloor(raw_volume/step+1e-9)*step" in text
    assert "OrderCalcMargin(order_type,_Symbol,sized,entry,required_margin)" in text
    assert "OrderCheck(request,check) || check.retcode!=0" in text
    assert text.count("OrderSend(request,result)") == 2
    assert "g_entry_request_pending" not in text


def test_contract_is_no_indicator_telemetry_off_baseline() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["telemetry_profile"] == "none"
    assert "indicator_dependencies" not in contract
    profile = contract["execution_profile"]
    assert profile["authority"] == "registered-untuned-model0-baseline"
    assert profile["timeframe"] == "M5"
    assert profile["expected_symbol"] == "EURUSD"
    assert profile["closed_bar_only"] is True
    assert profile["no_trade_api"] is False
    assert profile["promotion_eligible"] is False


def test_prereg_matches_runtime_boundary_choices() -> None:
    text = PREREG.read_text(encoding="utf-8")
    assert "`2016.01.04-2021.01.01`" in text
    assert "`20:00` broker-server time" in text
    assert "PF `>1.30`" in text
    assert "cadence `2-5/week`" in text
    assert "x1.5-cost PF `>=1.25`" in text
    assert "x2-cost PF `>=1.00`" in text


def test_fresh_compile_is_zero_error_zero_warning() -> None:
    assert EX5.is_file() and EX5.stat().st_size > 0
    log = COMPILE_LOG.read_text(encoding="utf-16", errors="replace")
    assert log.count("Result: 0 errors, 0 warnings") == 1
