from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
PLAN = ROOT / "research" / "HYP-ICT-FVG-FID-EURUSD-M5-001_PROBE_PLAN.md"
NEWS_PLAN = ROOT / "research" / "HYP-ICT-FVG-FIDNEWS-EURUSD-M5-002_PROBE_PLAN.md"
MATRIX = ROOT / "research" / "REQUIREMENT_TO_CODE_MATRIX.md"
PARENT_SNAPSHOT = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-FIDM0-EURUSD-M5-006.mq5"
)


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_source_exists_and_binds_identity() -> None:
    text = source_text()
    assert 'const string EA_NAME="EA_ICTFVGReportFidelity"' in text
    assert (
        'const string HYPOTHESIS_ID="HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"'
        in text
    )
    assert 'const string TELEMETRY_PROFILE="lifecycle-v3"' in text


def test_context_child_preserves_parent_inputs_except_frozen_context_surface() -> None:
    def inputs(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.startswith("input ")]

    assert PARENT_SNAPSHOT.is_file()
    current = inputs(source_text())
    context = [line for line in current if "InpContext" in line]
    human = [line for line in current if "InpHuman" in line]
    friday = [line for line in current if "InpFridayFlatten" in line]
    inherited = [
        line
        for line in current
        if "InpContext" not in line
        and "InpHuman" not in line
        and "InpFridayFlatten" not in line
    ]
    assert inherited == inputs(PARENT_SNAPSHOT.read_text(encoding="utf-8"))
    assert context == [
        "input int              InpContextMaxBars=3;",
        "input double           InpContextBodyMultiple=1.00;",
        "input double           InpContextCloseFraction=0.25;",
    ]
    assert friday == [
        "input int              InpFridayFlattenUtcHour=20;",
        "input int              InpFridayFlattenUtcMinute=55;",
    ]
    assert human == [
        "input int              InpHumanRangeBars=20;",
        "input int              InpHumanPivotStrength=2;",
        "input int              InpHumanPivotLookback=120;",
        "input int              InpHumanAtrPeriod=14;",
    ]


def test_frozen_surface_is_present() -> None:
    text = source_text()
    required = [
        "InpSignalMode",
        "InpRiskPercent",
        "InpPivotStrength",
        "InpSweepLookback",
        "InpDisplacementBars",
        "InpMeanBodyPeriod",
        "InpDisplacementBodyMultiple",
        "InpM15PivotStrength",
        "InpM15Lookback",
        "InpRetestBars",
        "InpFvgDepthMin",
        "InpFvgDepthMax",
        "InpAdxPeriod",
        "InpMinAdx",
        "InpStopBufferPips",
        "InpTargetRR",
        "InpMaxSpreadPips",
        "InpDailyLossPct",
        "InpMaxAccountDrawdownPct",
        "InpMaxConsecutiveLosses",
        "InpCooldownMinutes",
        "InpBreakEvenTriggerR",
        "InpBreakEvenLockR",
        "InpFlattenUtcHour",
        "InpRequireNewsGuard",
    ]
    for token in required:
        assert token in text


def test_ordered_fsm_and_exact_gates_are_explicit() -> None:
    text = source_text()
    required = [
        "SETUP_SWEPT",
        "SETUP_DISPLACED",
        "SETUP_MSS_CONFIRMED",
        "DetectSweep",
        "AdvanceDisplacement",
        "AdvanceM15Mss",
        "AdvanceRetest",
        "FindFreshOrderBlock",
        "OverlapZone",
        "ClosedM15Adx",
        "mean_body",
        "InpDisplacementBodyMultiple*mean_body",
    ]
    for token in required:
        assert token in text


def test_closed_bar_only_signal_surface() -> None:
    text = source_text()
    assert "CopyRates(_Symbol,PERIOD_M5,1," in text
    assert "CopyRates(_Symbol,PERIOD_M15,1," in text
    assert "CopyBuffer(g_adx_handle,0,1,1" in text
    assert "iTime(_Symbol,PERIOD_M5,0)" in text  # new-bar clock only
    assert "CopyRates(_Symbol,PERIOD_M5,0," not in text
    assert "CopyRates(_Symbol,PERIOD_M15,0," not in text


def test_risk_and_execution_guards() -> None:
    text = source_text()
    required = [
        "OrderCalcProfit",
        "OrderCheck",
        "DailyLossHit",
        "AccountDrawdownHit",
        "CooldownActive",
        "ManageOwnedPosition",
        "ReconcileActualFillRisk",
        "ServerToUtc",
        "InpFlattenUtcHour",
        "POSITION_MAGIC",
    ]
    for token in required:
        assert token in text


def test_lifecycle_v3_surface() -> None:
    text = source_text()
    assert "LifecycleTrades" in text
    assert "RunMeta" in text
    assert "OnTradeTransaction" in text
    assert '"is_final_close"' in text


def test_parent_freeze_and_news_child_contract_are_both_preserved() -> None:
    parent_plan = PLAN.read_text(encoding="utf-8")
    news_plan = NEWS_PLAN.read_text(encoding="utf-8")
    matrix = MATRIX.read_text(encoding="utf-8")
    assert "2023 onward is sealed holdout" in parent_plan
    assert "Historical high-impact news +/-30 minute filtering is `UNMET`" in parent_plan
    assert "No optimization" in parent_plan
    assert "2023 onward remains sealed and must not be loaded" in news_plan
    assert "1,282 timed EUR/USD high-impact events" in news_plan
    assert "248D569B981564AC0B179588C4919CD6CC196A9E7B008939A9CCDB3446F4678C" in news_plan
    assert "| News | Historical high-impact +/-30 minutes | `implemented_proxy` |" in matrix
