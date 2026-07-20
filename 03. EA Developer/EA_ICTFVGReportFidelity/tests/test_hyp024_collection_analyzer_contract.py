from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "research" / "analyze_hyp024_time_resilience_collection.py"


def text() -> str:
    return ANALYZER.read_text(encoding="utf-8")


def test_analyzer_is_bound_to_the_frozen_single_run_contract() -> None:
    source = text()
    assert "HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024" in source
    assert "3BC2130CE8F84AF44C6D3EFEC0639A7B461907A096A6AE90636479E6BB40E77B" in source
    assert "C9E1C59FF6B3A3D16B546A03362936F2CC6D3D8723704FFF88C04FB4EBF59073" in source
    assert "MIN_LABEL_SHARE = 0.20" in source
    assert "MIN_LABEL_CADENCE = 2.0" in source


def test_analyzer_derives_duration_identity_and_natural_label_only() -> None:
    source = text()
    assert "LEVEL_COLUMNS" in source and "HUMAN_COLUMNS" in source
    assert '"favorable_ms"' in source and '"adverse_ms"' in source
    assert "total_ms == decision_msc - first_favorable_msc" in source
    assert 'derived_label = "FAVORABLE_DOMINANT"' in source
    assert 'derived_label = "ADVERSE_DOMINANT"' in source
    assert "report.html" not in source


def test_analyzer_forbids_economic_and_future_result_keys() -> None:
    source = text()
    for token in (
        '"pnl"', '"profit"', '"drawdown"', '"balance"', '"equity"',
        '"commission"', '"swap"', '"mfe"', '"mae"', '"exit"',
        '"future_price"',
    ):
        assert token in source
    assert "assert_no_forbidden_result_keys(first)" in source


def test_result_gate_has_no_threshold_or_label_rescue() -> None:
    source = text()
    assert "PASS_OPEN_SEPARATE_PRE_ECONOMIC_HYP025" in source
    assert "KILL_AT_HYP024_COLLECTION_DATA_DENSITY_OR_REDUNDANCY" in source
    assert "MIN_LABEL_SHARE = 0.20" in source
    assert "MIN_LABEL_CADENCE = 2.0" in source
