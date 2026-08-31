from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "03. EA Developer" / "EA_MultiAssetTSMOMD1V6"
SOURCE = PACKAGE / "EA_MultiAssetTSMOMD1V6.mq5"


def test_v6_identity_and_universe_are_frozen() -> None:
    source = SOURCE.read_text(encoding="utf-8-sig")
    assert 'HYPOTHESIS_ID="HYP-MULTI-TSMOM-D1-006"' in source
    assert "#define ASSET_COUNT 8" in source
    assert source.count("AFD_") == 9  # expected host plus eight array rows
    assert "BTC" not in source
    assert "260812009" in source and "260812010" in source
    assert "AFD_EURUSD_DUKA_TSMOM_V5" not in source
    assert 'EXPECTED_SYMBOL="EURUSD_AFD_TSMOM_V6"' in source


def test_v6_uses_completed_d1_and_downward_only_caps() -> None:
    source = SOURCE.read_text(encoding="utf-8-sig")
    assert "CopyRates(g_symbols[index],PERIOD_D1,1,HISTORY_BUFFER,rates)" in source
    assert "MathMin(SINGLE_WEIGHT_CAP" in source
    assert "MathMin(g_weight[7],XAU_WEIGHT_CAP)" in source
    assert "InpLongOnlyComparator" in source
    assert "g_signal[i]=1.0" in source


def test_v6_source_selection_excludes_failed_btc_before_economics() -> None:
    receipt = json.loads(
        (PACKAGE / "research" / "HYP-MULTI-TSMOM-D1-006_SOURCE_SELECTION_RECEIPT.json")
        .read_text(encoding="utf-8")
    )
    assert receipt["status"] == "PASS_SELECTED_EIGHT_SYMBOL_SOURCE_ONLY"
    assert receipt["selection_frozen_before_any_parent_or_child_economics"] is True
    assert len(receipt["selected_symbols"]) == 8
    assert all(row["within_one_point_rate"] == 1.0 for row in receipt["selected_symbols"])
    assert receipt["excluded_symbols"][0]["symbol"] == "BTCUSD"
    assert receipt["economics_authorized"] is False


def test_v6_nonrepaint_manifest_matches_static_contract() -> None:
    manifest = json.loads(
        (PACKAGE / "HYP-MULTI-TSMOM-D1-006_NONREPAINT_MANIFEST.json")
        .read_text(encoding="utf-8")
    )
    assert manifest["audit_status"] == "PASS_STATIC"
    assert manifest["repaint_or_lookahead_detected"] is False
    assert manifest["current_bar_price_used"] is False
    assert len(manifest["universe"]) == 8


def test_v6_emits_fail_closed_data_epoch_series_proof() -> None:
    source = SOURCE.read_text(encoding="utf-8-sig")
    assert "bool EmitSeriesProof()" in source
    assert "DATA_EPOCH_D0_SERIES_PROOF symbol=%s" in source
    assert "if(!EmitSeriesProof())" in source
    assert "return INIT_FAILED;" in source


def test_v6_fails_closed_on_broken_custom_symbol_profit_spec() -> None:
    source = SOURCE.read_text(encoding="utf-8-sig")
    assert "bool ValidateTradeProfitSpecs()" in source
    assert "bool ValidateTradeStaticSpecs()" in source
    assert "OrderCalcProfit(ORDER_TYPE_BUY" in source
    assert "MTS006_PROFIT_SPEC symbol=%s" in source
    assert "!ValidateTradeProfitSpecs()" in source
    assert "if(!ValidateTradeStaticSpecs())" in source
