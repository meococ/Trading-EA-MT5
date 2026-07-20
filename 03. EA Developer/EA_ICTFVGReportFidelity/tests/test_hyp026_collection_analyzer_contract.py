from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "research" / "analyze_hyp026_pivot_reclaim_dwell_collection.py"


def text() -> str:
    return ANALYZER.read_text(encoding="utf-8")


def test_analyzer_is_bound_to_the_frozen_single_run_contract() -> None:
    source = text()
    assert "HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026" in source
    assert "227A52E93713731EF639D9484DABC89B85006660F436C0F232117C60F1528127" in source
    assert "7837739CC7FDED1ECE0C09EB66840466413AFC12C898706217EF4605422BF108" in source
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
    assert "PASS_OPEN_SEPARATE_PRE_ECONOMIC_HYP027" in source
    assert "KILL_AT_HYP026_COLLECTION_DATA_DENSITY_OR_REDUNDANCY" in source
    assert "MIN_LABEL_SHARE = 0.20" in source
    assert "MIN_LABEL_CADENCE = 2.0" in source



def test_analyzer_binds_green_build_receipt_without_economic_reads() -> None:
    source = text()
    assert '(build.get("package_regression") or {}).get("passed") == 105' in source
    assert '(build.get("source") or {}).get("sha256") == EXPECTED_SOURCE_SHA256' in source

