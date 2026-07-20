from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "research" / "analyze_hyp022_level_churn_collection.py"


def text() -> str:
    return ANALYZER.read_text(encoding="utf-8")


def test_analyzer_is_bound_to_the_frozen_single_run_contract() -> None:
    source = text()
    assert "HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022" in source
    assert "5FF5F8600362C95DAC66C2F1450A2B82D4E1B202F98679B9BE0C52C71039410C" in source
    assert "C7D8383F757E852921E1B0BB8FCFF5ACFD84B305BF959628DA3EC68034B77C3D" in source
    assert "MIN_LABEL_SHARE = 0.20" in source
    assert "MIN_LABEL_CADENCE = 2.0" in source


def test_analyzer_reads_only_frozen_sidecars_and_manifest_fields() -> None:
    source = text()
    assert "LEVEL_COLUMNS" in source and "HUMAN_COLUMNS" in source
    assert '"adverse_reentry_count"' in source
    assert '"UNDEFINED"' in source
    assert '("ORDERLY" if reentries <= 1 else "REPEATED_CHURN")' in source
    assert "report.html" not in source
    assert "load_level_rows" in source
    assert "data_rows(tick_path)" in source


def test_analyzer_forbids_economic_and_future_result_keys() -> None:
    source = text()
    for token in (
        '"pnl"', '"profit"', '"drawdown"', '"balance"', '"equity"',
        '"commission"', '"swap"', '"mfe"', '"mae"', '"exit"',
        '"future_price"',
    ):
        assert token in source
    assert "assert_no_forbidden_result_keys(first)" in source


def test_result_gate_cannot_rescue_the_frozen_threshold() -> None:
    source = text()
    assert "PASS_OPEN_SEPARATE_PRE_ECONOMIC_HYP023" in source
    assert "KILL_AT_HYP022_COLLECTION_DATA_DENSITY_OR_REDUNDANCY" in source
    assert "alternate" not in source.lower()
