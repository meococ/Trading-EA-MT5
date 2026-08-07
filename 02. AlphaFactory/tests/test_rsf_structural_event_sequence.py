from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "03. EA Developer" / "EA_RegimeStructureFusion" / "EA_RegimeStructureFusion.mq5"
TB_SOURCE = ROOT / "06.Indicator Alpha" / "TB_Smart_Money_Concept_2026.mq5"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8-sig")


def tb_source_text() -> str:
    return TB_SOURCE.read_text(encoding="utf-8-sig")


def test_structural_event_path_is_opt_in_and_exclusive() -> None:
    text = source_text()
    assert "input bool   InpUseStructuralEventSequence=false" in text
    assert (
        "if((int)InpUseTemporalSequence+(int)InpUseRoleAwareSequence+"
        "(int)InpUseStructuralEventSequence>1) return(false);"
    ) in text
    assert "InpUseStructuralEventSequence ? BuildStructuralEventDecision" in text


def test_exact_closed_tb_event_owns_the_arm() -> None:
    text = source_text()
    assert "ReadClosed1(g_tb,27,tb_structure_event)" in text
    assert "ReadClosed1(g_tb,29,s.tb_structure_level)" in text
    assert "ReadClosed1(g_tb,17,s.tb_trail_high)" in text
    assert "ReadClosed1(g_tb,18,s.tb_trail_low)" in text
    assert "ReadClosed1(g_tb,11,tb_displacement_up_exact)" in text
    assert "ReadClosed1(g_tb,12,tb_displacement_down_exact)" in text
    assert "ArmStructuralEvent(event_signal,s); return(false);" in text


def test_retest_reclaim_is_later_and_uses_only_closed_bar_prices() -> None:
    text = source_text()
    assert "if(age>=1 && StructuralRetestReclaimed" in text
    assert "s.high_price=iHigh(_Symbol,PERIOD_M5,1);" in text
    assert "s.low_price=iLow(_Symbol,PERIOD_M5,1);" in text
    assert "s.close_price=iClose(_Symbol,PERIOD_M5,1);" in text
    assert "iHigh(_Symbol,PERIOD_M5,0)" not in text
    assert "iLow(_Symbol,PERIOD_M5,0)" not in text


def test_structural_objective_must_pay_and_caps_the_target() -> None:
    text = source_text()
    assert "input bool   InpStructuralRequireLiveObjective=false" in text
    assert "if(InpStructuralRequireLiveObjective && objective<=0.0)" in text
    assert "if(InpStructuralRequireLiveObjective)" in text
    assert "g_structural_reject_no_objective++" in text
    assert "objective_room/risk+1e-12<InpStructuralMinObjectiveR" in text
    assert "fixed_target=entry+d.direction*risk*InpRewardRisk" in text
    assert "MathMin(fixed_target,g_structural_objective)" in text
    assert "MathMax(fixed_target,g_structural_objective)" in text


def test_context_and_qqe_are_vetoes_not_entry_triggers() -> None:
    text = source_text()
    assert "bool StructuralContextVeto" in text
    assert "bool StructuralQqeVeto" in text
    structural_start = text.index("bool BuildStructuralEventDecision")
    structural_end = text.index("bool SubmitEntry", structural_start)
    body = text[structural_start:structural_end]
    assert "RoleQqeCrossedZero" not in body
    assert "RoleQqeReaccelerated" not in body


def test_structural_funnel_is_exported() -> None:
    text = source_text()
    for name in (
        "structural_armed",
        "structural_retested",
        "structural_confirmed",
        "structural_expired",
        "structural_canceled",
        "structural_reject_context",
        "structural_reject_no_objective",
        "structural_reject_runway",
    ):
        assert f'\\"{name}\\"' in text


def test_entry_context_sidecar_observes_the_accepted_closed_bar_decision() -> None:
    text = source_text()
    assert 'StringFormat("%s_EntryContext_%s.csv",_Symbol,g_run_id)' in text
    assert '"structural_objective","objective_room_r"' in text
    assert '"tb_swing_high_live","tb_swing_low_live"' in text
    assert '"tb_structure_event"' in text
    assert "void LogEntryContext(const TradeDecision &d,const RsfSnapshot &s" in text
    assert "LogEntryContext(d,s,request,result);" in text
    assert "SubmitEntry(decision,snapshot)" in text


def test_liquidity_pool_objective_is_opt_in_and_version_bound() -> None:
    text = source_text()
    assert "const double RSF_REQUIRED_TB_CONTRACT_VERSION=3.0;" in text
    assert "input bool   InpStructuralUseLiquidityPoolObjective=false" in text
    assert "s.tb_liquidity_high=OptionalClosed1(g_tb,44,0.0);" in text
    assert "s.tb_liquidity_low=OptionalClosed1(g_tb,45,0.0);" in text
    assert "ReadClosed1(g_tb,46,tb_liquidity_high_live)" in text
    assert "ReadClosed1(g_tb,47,tb_liquidity_low_live)" in text
    assert "if(InpStructuralUseLiquidityPoolObjective)" in text


def test_tb_liquidity_pool_is_closed_bar_causal_and_bounded() -> None:
    text = tb_source_text()
    assert "const double TB_CONTRACT_VERSION=3.0;" in text
    assert "#property indicator_plots   48" in text
    assert "for(int plot=2;plot<48;plot++)" in text
    assert "const int    TB_MAX_LIQUIDITY_LEVELS=64;" in text
    assert "PushLiquidityFront(g_highLiquidity,pivotValue,pivotIndex);" in text
    assert "PushLiquidityFront(g_lowLiquidity,pivotValue,pivotIndex);" in text
    assert "ConsumeClosedLiquidity(close[index]);" in text
    assert "if(closedPrice>g_highLiquidity[i].price)" in text
    assert "if(closedPrice<g_lowLiquidity[i].price)" in text
    assert "while(ArraySize(pool)>TB_MAX_LIQUIDITY_LEVELS)" in text


def test_consumed_break_level_cannot_be_published_as_forward_liquidity() -> None:
    text = tb_source_text()
    consume = text.index("ConsumeClosedLiquidity(close[index]);")
    publish = text.index("PublishEngineState(index,true,close[index]);")
    assert consume < publish
    assert "if(level<=referencePrice)" in text
    assert "if(level>=referencePrice)" in text


def test_entry_context_exports_pool_objective_state() -> None:
    text = source_text()
    assert '"tb_liquidity_high","tb_liquidity_low"' in text
    assert '"tb_liquidity_high_live","tb_liquidity_low_live"' in text
    assert "DoubleToString(s.tb_liquidity_high,_Digits)" in text
    assert "DoubleToString(s.tb_liquidity_low,_Digits)" in text
