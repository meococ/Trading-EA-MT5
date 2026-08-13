from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "03. EA Developer/EA_MultiAssetTSMOMD1V1/EA_MultiAssetTSMOMD1V1.mq5"
PREREG = ROOT / "03. EA Developer/EA_MultiAssetTSMOMD1V1/research/HYP-MULTI-TSMOM-D1-001_FROZEN_DESIGN_PREREG.md"


def test_frozen_identity_and_closed_bar_formula():
    text = SOURCE.read_text(encoding="utf-8")
    assert 'HYPOTHESIS_ID="HYP-MULTI-TSMOM-D1-001"' in text
    assert "PERIOD_D1,1,FORMATION_CLOSES" in text
    assert "closes[0]/closes[FORMATION_CLOSES-1]-1.0" in text
    assert "VOL_RETURN_COUNT=60" in text
    assert "CopyClose(g_symbols[index],PERIOD_D1,1" in text
    assert "CopyClose(g_symbols[index],PERIOD_D1,0" not in text


def test_exact_universe_and_caps_are_bound():
    text = SOURCE.read_text(encoding="utf-8")
    for symbol in ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF", "XAUUSD", "BTCUSD"):
        assert f'"{symbol}"' in text
    for token in ("SINGLE_WEIGHT_CAP=0.18", "FX_GROSS_CAP=0.70", "USD_FACTOR_CAP=0.25", "TOTAL_GROSS_CAP=1.00"):
        assert token in text


def test_no_signal_rescue_primitives():
    text = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("iATR(", "iADX(", "iMA(", "take_profit", "request.tp=", "request.sl="):
        assert forbidden not in text


def test_prereg_keeps_future_splits_sealed():
    text = PREREG.read_text(encoding="utf-8")
    assert "VALIDATION: `[2022-01-01, 2024-01-01)` sealed" in text
    assert "HOLDOUT: `[2024-01-01, latest]` sealed" in text
    assert "No lookback, universe, cap, direction" in text
