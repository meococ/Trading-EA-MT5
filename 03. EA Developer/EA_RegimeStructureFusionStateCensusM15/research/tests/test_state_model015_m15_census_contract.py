from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "EA_RegimeStructureFusionStateCensusM15.mq5").read_text(encoding="utf-8")


def test_base_period_is_mapped_only_inside_include():
    assert "#define PERIOD_M5 PERIOD_M15" in SOURCE
    assert '#include "..\\EA_RegimeStructureFusion\\EA_RegimeStructureFusion.mq5"' in SOURCE
    assert "#undef PERIOD_M5" in SOURCE


def test_export_uses_native_m15_closed_bar():
    assert "iTime(_Symbol,PERIOD_M15,1)" in SOURCE
    assert "iOpen(_Symbol,PERIOD_M15,1)" in SOURCE
    assert "iClose(_Symbol,PERIOD_M15,1)" in SOURCE


def test_all_direct_entry_modes_fail_closed():
    assert "if(InpAllowRangeMode || InpAllowTrendMode || InpAllowBreakoutMode) return(false);" in SOURCE


def test_all_sequence_and_path_routes_fail_closed():
    assert "InpUseTemporalSequence || InpUseRoleAwareSequence || InpUseStructuralEventSequence || InpUsePathManagement" in SOURCE


def test_snapshot_is_exported_only_after_base_closed_bar_counter_advances():
    assert "long before=g_closed_bars_seen;" in SOURCE
    assert "if(g_closed_bars_seen>before) ExportCensusClosedBar();" in SOURCE


def test_output_contains_all_five_indicator_families():
    for field in ("aird_regime", "vrc_regime", "mbb_basis", "tb_bias", "qqe_primary"):
        assert f'"{field}"' in SOURCE


def test_census_window_and_flush_are_bounded():
    assert "InpCensusTo<=InpCensusFrom" in SOURCE
    assert "InpCensusFlushEveryRows<1 || InpCensusFlushEveryRows>100000" in SOURCE
