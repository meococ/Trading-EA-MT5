from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
PREREG = PACKAGE / "research/HYP-GMP-XAU-M15-REALYIELD-001_FROZEN_PREREG.md"
PROBE = PACKAGE / "research/gold_real_yield_offline_probe.py"
DATA = PACKAGE / "research/data/DFII10_2019_2024.csv"


def test_external_data_is_frozen_train_only_and_hash_bound():
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "FROZEN BEFORE FIRST PROBE" in prereg
    assert "2024.12.31" in prereg
    assert "2025+ is untouched" in prereg
    assert "C22544C463731D9EE153B5C87D53FCE2B45DF606841263E9F40E833071A0ADED" in prereg
    assert "dfii10_train_sha256" in source
    assert DATA.is_file()


def test_h15_signal_is_lagged_and_never_uses_same_day_value():
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "first later XAU trading date" in prereg
    assert "bisect.bisect_right" in source
    assert "bisect.bisect_left" not in source
    assert "signal_date = trading_dates[position]" in source
    assert "ENTRY_HOUR_UTC = 14" in source
    assert "ENTRY_MINUTE_UTC = 30" in source


def test_probe_has_one_parameter_set_matched_control_and_all_gates():
    source = PROBE.read_text(encoding="utf-8")
    assert "YIELD_SHOCK_PERCENTAGE_POINTS = 0.05" in source
    assert "STOP_ATR_MULT = 1.5" in source
    assert "TARGET_R = 1.5" in source
    assert "COST_PROXY_POINTS = 82.0" in source
    assert '"control"' in source
    assert '"challenger"' in source
    assert source.index("if entry_idx < 97:") < source.index("momentum_direction(frame, entry_idx)")
    assert "optimiz" not in source.lower()
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


def test_execution_is_closed_bar_and_intrabar_conservative():
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "completed bars" in prereg
    assert "stop wins same-bar ambiguity" in prereg
    assert "atr[entry_idx - 1]" in source
    assert "frame.loc[entry_idx - 1" in source
    assert source.index("if stopped:") < source.index("if targeted:")
    assert "allow_nan=False" in source
    assert "portable=True" in source
