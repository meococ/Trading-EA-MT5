from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
H001_SPEC = PACKAGE / "research/HYP-PO3-AMD-SCALP-M5-XAU-001_PROBE_SPEC.md"
PREREG = PACKAGE / "research/HYP-PO3-AMD-SCALP-M5-XAU-003_FROZEN_PREREG.md"
PROBE = PACKAGE / "research/po3_amd_xau_ny_probe.py"


def test_ny_branch_was_predeclared_and_has_a_fresh_id():
    h001 = H001_SPEC.read_text(encoding="utf-8")
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "NY continuation is deferred to a" in h001
    assert "separate hypothesis" in h001
    assert "HYP-PO3-AMD-SCALP-M5-XAU-003" in prereg
    assert "FROZEN BEFORE FIRST PROBE" in prereg
    assert 'HYPOTHESIS_ID = "HYP-PO3-AMD-SCALP-M5-XAU-003"' in source


def test_ny_window_is_exact_and_other_thresholds_are_inherited_frozen():
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "07:00 <= ET < 10:00" in prereg
    assert 'dt.hour >= 7' in source
    assert 'dt.hour < 10' in source
    assert "420 <= minute < 600" in source
    assert "normalized.ASIA_MIN_RANGE_ATR" in source
    assert "base.DISPLACEMENT_ATR" in source
    assert "base.RETEST_BARS" in source


def test_ny_probe_remains_train_only_closed_bar_and_hashes_dependencies():
    prereg = PREREG.read_text(encoding="utf-8")
    source = PROBE.read_text(encoding="utf-8")
    assert "2024.12.31" in prereg
    assert "2025+ remains" in prereg
    assert "sweep_idx + 1" in source
    assert "retest_idx + 1" in source
    assert "NORMALIZED_DEPENDENCY" in source
    assert "H001_BASE_DEPENDENCY" in source
    assert "normalized.gate_metrics" not in source
    assert "normalized.main()" in source

