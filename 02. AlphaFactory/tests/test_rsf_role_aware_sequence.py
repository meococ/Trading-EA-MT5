from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "03. EA Developer" / "EA_RegimeStructureFusion" / "EA_RegimeStructureFusion.mq5"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_role_aware_path_is_opt_in_and_exclusive_with_legacy_sequence() -> None:
    text = source_text()
    assert "input bool   InpUseRoleAwareSequence=false" in text
    assert (
        "if((int)InpUseTemporalSequence+(int)InpUseRoleAwareSequence+"
        "(int)InpUseStructuralEventSequence>1) return(false);"
    ) in text
    assert "InpUseRoleAwareSequence ? BuildRoleAwareDecision" in text


def test_each_indicator_has_one_explicit_role() -> None:
    text = source_text()
    assert "AIRD owns slow state" in text
    assert "VRC owns volatility permissions" in text
    assert "TB owns direction/price invalidation" in text
    assert "MBB owns location/objective" in text
    assert "QQE is allowed to trigger only after price" in text


def test_breakout_requires_later_retest_and_later_trigger() -> None:
    text = source_text()
    assert "g_role_stage=IsBreakoutSignal(signal) ? RSF_ROLE_WAIT_RETEST" in text
    assert "if(age>=1 && touched)" in text
    assert "g_role_stage_bar_time=g_last_bar_time" in text
    assert "if(stage_age>=1 && RoleTriggerReady" in text
    assert "extension<=InpRoleBreakoutMaxTriggerExtensionAtr*s.tb_atr" in text


def test_trend_and_range_use_qqe_zero_cross_after_arm() -> None:
    text = source_text()
    assert "bool RoleQqeCrossedZero" in text
    assert "s.qqe_primary_prev<=0.0" in text
    assert "s.qqe_primary_prev>=0.0" in text
    assert "reclaimed && located && RoleQqeCrossedZero" in text
    assert "reclaimed && inside && entry_half && RoleQqeCrossedZero" in text


def test_range_target_is_basis_and_must_pay_minimum_r() -> None:
    text = source_text()
    assert "double reward=d.direction*(s.mbb_basis-entry);" in text
    assert "reward/risk+1e-12<InpRoleRangeMinTargetR" in text
    assert "d.target=NormalizeDouble(s.mbb_basis,_Digits);" in text


def test_retest_uses_closed_bar_high_low_not_live_bar_zero() -> None:
    text = source_text()
    assert "s.high_price=iHigh(_Symbol,PERIOD_M5,1);" in text
    assert "s.low_price=iLow(_Symbol,PERIOD_M5,1);" in text
    assert "s.close_price=iClose(_Symbol,PERIOD_M5,1);" in text
    assert "iHigh(_Symbol,PERIOD_M5,0)" not in text
    assert "iLow(_Symbol,PERIOD_M5,0)" not in text


def test_role_state_counters_are_exported() -> None:
    text = source_text()
    for name in (
        "role_armed",
        "role_retested",
        "role_confirmed",
        "role_expired",
        "role_canceled",
        "role_reject_ambiguity",
    ):
        assert f'\\"{name}\\"' in text
