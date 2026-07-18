from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
PREREG = PACKAGE / "research/HYP-PO3-AMD-SCALP-M5-XAU-002_FROZEN_PREREG.md"
PROBE = PACKAGE / "research/po3_amd_xau_normalized_probe.py"


def test_normalized_hypothesis_is_new_frozen_and_train_only():
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "HYP-PO3-AMD-SCALP-M5-XAU-002" in prereg
    assert "FROZEN BEFORE FIRST PROBE" in prereg
    assert "2024.12.31" in prereg
    assert "Calendar year 2025" in prereg
    assert "remain untouched holdout data" in prereg
    assert "HYPOTHESIS_ID = \"HYP-PO3-AMD-SCALP-M5-XAU-002\"" in source
    assert "base.load_rates" in source


def test_normalization_is_source_derived_and_not_observed_percentile_tuning():
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "80 / 60" in prereg
    assert "300 / 20" in prereg
    assert "ASIA_MIN_RANGE_ATR = 80.0 / 60.0" in source
    assert "ASIA_MAX_RANGE_ATR = 300.0 / 20.0" in source
    assert "percentile" not in source.lower()
    assert "np.median(asia_atr)" in source


def test_closed_bar_sequence_control_and_all_economic_gates_are_bound():
    source = PROBE.read_text(encoding="utf-8")
    assert "sweep_idx + 1" in source
    assert "retest_idx + 1" in source
    assert '"control"' in source
    for token in (
        '"cadence_min"',
        '"cadence_max"',
        '"pf"',
        '"expectancy"',
        '"drawdown"',
        '"positive_years"',
        '"net_positive_and_not_below_control"',
        '"pf_margin_over_control"',
    ):
        assert token in source
    assert "allow_nan=False" in source
