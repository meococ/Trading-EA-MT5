from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SPEC = PACKAGE / "research/HYP-PO3-AMD-SCALP-M5-XAU-001_PROBE_SPEC.md"
PROBE = PACKAGE / "research/po3_amd_xau_offline_probe.py"


def test_probe_is_frozen_to_train_only_and_closed_bar_execution():
    spec = SPEC.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "2024-12-31" in spec
    assert "TO_UTC = datetime(2024, 12, 31" in source
    assert "TO_UTC = datetime(2025" not in source
    assert "next M5" in spec
    assert "sweep_idx + 1" in source


def test_probe_has_single_parameter_set_and_no_optimizer_surface():
    source = PROBE.read_text(encoding="utf-8")
    assert "optimiz" not in source.lower()
    assert "DISPLACEMENT_ATR = 1.5" in source
    assert "COST_PROXY_PTS = 35.0" in source
    assert "CONTINUE_TO_PREREG" in source
    assert "KILL_AT_OFFLINE_PROBE" in source
    assert '"profit_factor_infinite": pf_infinite' in source
    assert "allow_nan=False" in source


def test_probe_gates_include_control_separation_and_workspace_economics():
    source = PROBE.read_text(encoding="utf-8")
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
