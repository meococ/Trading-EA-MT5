from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_VRAS_VolatilityNormalizedStop.mq5"


def text():
    return SOURCE.read_text(encoding="utf-8")


def test_source_exists():
    assert SOURCE.is_file()


def test_exact_hypothesis_and_variants():
    s = text()
    assert 'HYP-VRAS-EURUSD-M5-006' in s
    assert 'InpUseVolatilityNormalizedStop' in s
    assert 'CONTROL_FIXED_CLAMP' in s and 'CHALLENGER_ATR_STRUCTURAL' in s


def test_closed_bar_signal_and_indicators():
    s = text()
    assert 'CopyBuffer(g_h1_ema_handle,0,1,1' in s
    assert 'CopyBuffer(g_atr_handle,0,1,1' in s
    assert 'CopyRates(_Symbol,PERIOD_M5,1,3' in s
    assert 'CopyRates(_Symbol,PERIOD_M5,1,InpRollingVwapBars' in s
    assert 'history[index].tick_volume' in s


def test_one_change_stop_contract():
    s = text()
    assert 'InpControlMinSlPips=4.0' in s
    assert 'InpControlMaxSlPips=15.0' in s
    assert 'InpAtrFloorMultiple=1.0' in s
    assert 'InpMaxStructuralAtrMultiple=3.0' in s
    assert 'STRUCTURE_TOO_WIDE_REJECT' in s
    assert 'MathMax(raw_distance,atr*InpAtrFloorMultiple)' in s


def test_shared_geometry_is_frozen():
    s = text()
    assert 'InpRiskRewardRatio=1.5' in s
    assert 'InpBreakEvenTriggerR=1.0' in s
    assert 'InpBreakEvenOffsetPips=0.5' in s
    assert 'InpMaxHoldBars=24' in s


def test_complete_lifecycle_v3():
    s = text()
    assert 'void OnTradeTransaction' in s
    assert 'DEAL_COMMISSION' in s and 'DEAL_SWAP' in s and 'DEAL_FEE' in s
    assert 'initial_risk_account' in s and 'risk_pts' in s
    assert not re.search(r'FileWrite\([^;]+position_id,\s*0\.0,\s*0\.0', s, re.S)


def test_risk_guards_are_live_code_paths():
    s = text()
    for name in ['InpMaxTradesPerDay', 'InpDailyLossPct', 'InpMaxAccountDrawdownPct']:
        assert s.count(name) >= 3
    assert 'OrderCalcProfit' in s and 'OrderCheck' in s
    assert 'TesterStop' not in s and 'ExpertRemove' not in s


def test_hyp007_full_horizon_identity_is_explicit():
    s = text()
    assert 'HYP-VRAS-EURUSD-M5-007' in s
    assert 'InpDiagnosticDisableAccountDDEntryHalt' in s
    assert '5600757' in s
    assert 'CONTROL_FIXED_CLAMP_FULL_HORIZON' in s
    assert 'CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON' in s


def test_dd_threshold_is_measured_when_entry_halt_is_bypassed():
    s = text()
    assert 'g_account_dd_threshold_breached' in s
    assert 'g_max_initial_equity_dd_pct' in s
    assert 'g_max_peak_equity_dd_pct' in s
    assert 'if(!InpDiagnosticDisableAccountDDEntryHalt)' in s


def test_diagnostic_bypass_is_tester_only_and_micro_risk_bound():
    s = text()
    assert 'InpDiagnosticDisableAccountDDEntryHalt && !MQLInfoInteger(MQL_TESTER)' in s
    assert 'MathAbs(InpRiskPercent-0.05)' in s
    assert 'account_dd_entry_halt_enabled' in s
    assert 'account_dd_threshold_breached' in s
    assert 'max_initial_equity_dd_pct' in s
    assert 'max_peak_equity_dd_pct' in s


def test_hyp008_tester_survival_identity_only_extension():
    s = text()
    assert 'HYP-VRAS-EURUSD-M5-008' in s
    assert '5600758' in s
    assert 'MathAbs(InpRiskPercent-0.01)' in s
    assert 'CONTROL_FIXED_CLAMP_FULL_HORIZON_V2' in s
    assert 'CHALLENGER_ATR_STRUCTURAL_FULL_HORIZON_V2' in s
