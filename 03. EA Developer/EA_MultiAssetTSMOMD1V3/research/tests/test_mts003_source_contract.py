from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "03. EA Developer/EA_MultiAssetTSMOMD1V3/EA_MultiAssetTSMOMD1V3.mq5"
PREREG = ROOT / "03. EA Developer/EA_MultiAssetTSMOMD1V3/research/HYP-MULTI-TSMOM-D1-003_FROZEN_DESIGN_PREREG.md"


def source_text():
    return SOURCE.read_text(encoding="utf-8")


def test_frozen_identity_and_closed_bar_formula():
    text = source_text()
    assert 'HYPOTHESIS_ID="HYP-MULTI-TSMOM-D1-003"' in text
    assert "PERIOD_D1,1,FORMATION_CLOSES" in text
    assert "closes[0]/closes[FORMATION_CLOSES-1]-1.0" in text
    assert "VOL_RETURN_COUNT 60" in text
    assert "CopyClose(g_symbols[index],PERIOD_D1,0" not in text


def test_exact_universe_caps_and_no_signal_rescue():
    text = source_text()
    for symbol in ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF", "XAUUSD", "BTCUSD"):
        assert f'"{symbol}"' in text
    for token in ("SINGLE_WEIGHT_CAP=0.18", "FX_GROSS_CAP=0.70", "USD_FACTOR_CAP=0.25", "TOTAL_GROSS_CAP=1.00"):
        assert token in text
    for forbidden in ("iATR(", "iADX(", "iMA(", "request.tp=", "request.sl="):
        assert forbidden not in text


def test_snapshot_is_once_and_precedes_readiness_and_orders():
    text = source_text()
    process = text.split("void ProcessMonday", 1)[1].split("void RefreshDayBaseline", 1)[0]
    assert process.count("PrepareMondaySnapshot(g_pending_decision_time)") == 1
    assert "PlanVolumes()" not in text.split("bool PrepareMondaySnapshot", 1)[1].split("void ProcessMonday", 1)[0]
    assert process.index("PrepareMondaySnapshot") < process.index("CommonMarketReady")
    assert process.index("CommonMarketReady") < process.index('CloseAllOwned("MTS_WEEKLY")')
    assert process.index('CloseAllOwned("MTS_WEEKLY")') < process.index("PlanVolumes()")
    assert process.index("PlanVolumes()") < process.index("SubmitPlannedEntry")


def test_readiness_is_current_retry_causal_and_all_orders_are_guarded():
    text = source_text()
    readiness = text.split("bool CommonMarketReady", 1)[1].split("bool LoadClosedAssetState", 1)[0]
    assert "tick.time>retry_time" in readiness
    assert "retry_time-tick.time>60" in readiness
    assert "IsTradeSessionOpen" in readiness
    assert "g_common_readiness_armed" in text
    assert "g_orders_without_common_readiness" in text
    assert "code==TRADE_RETCODE_DONE;" in text


def test_prereg_keeps_future_splits_sealed_and_no_posthoc_cutoff():
    text = PREREG.read_text(encoding="utf-8")
    assert "VALIDATION `[2022-01-01, 2024-01-01)`" in text
    assert "HOLDOUT `[2024-01-01, latest]`" in text
    assert "There is no intra-Monday cutoff" in text
    assert "No lookback, universe, cap, direction" in text
