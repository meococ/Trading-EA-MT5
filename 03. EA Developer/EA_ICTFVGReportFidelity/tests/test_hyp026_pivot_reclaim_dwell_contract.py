import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
PARENT = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024.mq5"
)
PLAN = ROOT / "research" / "HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026_COLLECTION_PLAN.md"
MATRIX = ROOT / "research" / "HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026_LOGIC_TO_CODE_MATRIX.md"
PRESET = ROOT / "presets" / "EURUSD_M5_HYP026_PIVOT_RECLAIM_DWELL_COLLECT.set"

PARENT_SHA = "3BC2130CE8F84AF44C6D3EFEC0639A7B461907A096A6AE90636479E6BB40E77B"
PLAN_SHA = "4F963A8AC579F90828B2A669A08746E7CD9739116F367A68D5FF7FC511C8F059"
MATRIX_SHA = "78FCA7E09F133B64DF6FE7C928B73F9F0C777EDA5C625C1B2683564DCCAEB6F2"
PRESET_SHA = "C34A7FEF4CDDBDF18663DA81E66552B444A85666BC1B41D690289B02B20107D4"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def function_body(name: str, source: str | None = None) -> str:
    source = source_text() if source is None else source
    signature = source.index(f"{name}(")
    opening = source.index("{", signature)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
    raise AssertionError(f"unterminated function: {name}")


def integrate(
    level: float,
    direction: int,
    observations: list[tuple[int, float | None]],
    decision_msc: int,
) -> tuple[int, int, str]:
    side = 0
    first_favorable = False
    last_valid_msc = 0
    favorable_ms = 0
    adverse_ms = 0
    for time_msc, mid in observations:
        if mid is None:
            continue
        directed = direction * (mid - level)
        next_side = 1 if directed > 0 else -1 if directed < 0 else side
        if not first_favorable:
            if next_side != 1:
                continue
            first_favorable = True
            side = 1
            last_valid_msc = time_msc
            continue
        dt = max(0, time_msc - last_valid_msc)
        if side == 1:
            favorable_ms += dt
        elif side == -1:
            adverse_ms += dt
        side = next_side
        last_valid_msc = time_msc
    if first_favorable and decision_msc > last_valid_msc:
        dt = decision_msc - last_valid_msc
        if side == 1:
            favorable_ms += dt
        elif side == -1:
            adverse_ms += dt
    label = "UNDEFINED"
    if first_favorable and favorable_ms + adverse_ms > 0:
        if favorable_ms > adverse_ms:
            label = "FAVORABLE_DOMINANT"
        elif adverse_ms > favorable_ms:
            label = "ADVERSE_DOMINANT"
    return favorable_ms, adverse_ms, label


def test_frozen_parent_plan_matrix_and_preset() -> None:
    assert sha(PARENT) == PARENT_SHA
    assert sha(PLAN) == PLAN_SHA
    assert sha(MATRIX) == MATRIX_SHA
    assert sha(PRESET) == PRESET_SHA
    preset = PRESET.read_text(encoding="utf-8")
    assert "InpSignalMode=7" in preset
    assert "InpMagic=5600734" in preset
    assert "InpResearchAutoMode=false" in preset


def test_pivot_geometry_allows_adverse_dwell_without_extreme_invalidation() -> None:
    pivot_high = 100.0
    sweep_high = 102.0
    sweep_low = 98.0
    observations = [(0, 99.0), (1, 101.0), (9, 97.0)]
    favorable, adverse, label = integrate(pivot_high, -1, observations, 10)
    assert max(mid for _, mid in observations) < sweep_high
    assert observations[-1][1] < sweep_low
    assert (favorable, adverse, label) == (2, 8, "ADVERSE_DOMINANT")
    # The same observed path is always favorable relative to the old wick tip.
    assert integrate(sweep_high, -1, observations, 10) == (10, 0, "FAVORABLE_DOMINANT")


def test_same_ohlc_prices_can_flip_pivot_duration_label_by_timestamps() -> None:
    path_a = [(0, 101.0), (1, 99.0), (9, 109.0)]
    path_b = [(0, 101.0), (8, 99.0), (9, 109.0)]
    ohlc = lambda path: (path[0][1], max(p for _, p in path), min(p for _, p in path), path[-1][1])
    assert ohlc(path_a) == ohlc(path_b) == (101.0, 109.0, 99.0, 109.0)
    assert [p for _, p in path_a] == [p for _, p in path_b]
    assert integrate(100.0, 1, path_a, 10) == (2, 8, "ADVERSE_DOMINANT")
    assert integrate(100.0, 1, path_b, 10) == (9, 1, "FAVORABLE_DOMINANT")


def test_source_identity_mode_and_stored_pivot_are_explicit() -> None:
    text = source_text()
    assert '#property version   "1.27"' in text
    assert 'HYPOTHESIS_ID="HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"' in text
    assert "SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION=7" in text
    assert 'return "PIVOT_RECLAIM_DWELL_COLLECTION"' in function_body("SignalModeName", text)
    assert "double swept_pivot_level;" in text


def test_detect_sweep_passes_exact_predicate_pivot_to_setup() -> None:
    text = source_text()
    detect = function_body("DetectSweep", text)
    assert "bars[0].low<pivot_low && bars[0].close>pivot_low" in detect
    assert "bars[0].high>pivot_high && bars[0].close<pivot_high" in detect
    assert "double swept_pivot_level=(direction>0 ? pivot_low : pivot_high);" in detect
    assert "AddSweepSetup(direction,date_key,session_id,bars[0],swept_pivot_level," in detect


def test_mode_seven_uses_pivot_while_mode_six_keeps_sweep_extreme() -> None:
    text = source_text()
    add = function_body("AddSweepSetup", text)
    assert "g_setups[index].swept_pivot_level=swept_pivot_level;" in add
    assert "if(InpSignalMode==SIGNAL_TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION)" in add
    assert "g_setups[index].resilience_level=(direction>0 ? bar.low : bar.high);" in add
    marker = "if(InpSignalMode==SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION)"
    assert marker in add
    branch = add[add.index(marker) :]
    assert "g_setups[index].resilience_level=swept_pivot_level;" in branch
    assert "RegisterActiveResilienceSlot(index);" in branch


def test_mode_seven_reuses_exact_clock_semantics_and_compact_registry() -> None:
    text = source_text()
    register = function_body("RegisterActiveResilienceSlot", text)
    active = function_body("AccumulateActiveResilience", text)
    accumulator = function_body("AccumulateSetupResilience", text)
    assert "SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION" in register
    assert "SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION" in active
    assert "tick.time_msc-setup.resilience_last_valid_msc" in accumulator
    assert "setup.resilience_favorable_ms+=delta_msc" in accumulator
    assert "setup.resilience_adverse_ms+=delta_msc" in accumulator
    assert "next_side=setup.resilience_side" in accumulator


def test_mode_seven_logs_and_returns_before_order_path() -> None:
    text = source_text()
    advance = function_body("AdvanceContextState", text)
    detect = function_body("DetectSweep", text)
    process = function_body("ProcessClosedM5Bar", text)
    marker = "if(InpSignalMode==SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION)"
    assert marker in detect and marker in process
    start = advance.index(marker)
    trade = advance.index('TryOpenTrade(setup.direction,stop,"ICTFVG_CONTEXT_STATE")')
    branch = advance[start:trade]
    assert "LogLevelResilienceDecision" in branch
    assert "ClearSetup(setup)" in branch and "return;" in branch
    assert "TryOpenTrade" not in branch


def test_mode_seven_keeps_confirmation_and_decision_order_closed_bar_only() -> None:
    text = source_text()
    advance = function_body("AdvanceContextState", text)
    on_tick = function_body("OnTick", text)
    assert "bars[0].close<=setup.sweep_low" in advance
    assert "bars[0].close>=setup.sweep_high" in advance
    assert "bars[0].close>setup.sweep_high" in advance
    assert "bars[0].close<setup.sweep_low" in advance
    assert on_tick.index("ProcessClosedM5Bar()") < on_tick.rindex("AccumulateActiveResilience(tick)")


def test_level_resilience_telemetry_remains_auditable_and_zero_trade() -> None:
    text = source_text()
    opener = function_body("OpenLevelResilienceTelemetry", text)
    logger = function_body("LogLevelResilienceDecision", text)
    meta = function_body("WriteRunMeta", text)
    for field in (
        "event_id", "decision_msc", "direction", "level", "first_favorable_msc",
        "favorable_ms", "adverse_ms", "total_ms", "resilience_label",
        "interval_identity_valid", "duration_identity_valid",
    ):
        assert f'"{field}"' in opener
    assert '"FAVORABLE_DOMINANT"' in logger and '"ADVERSE_DOMINANT"' in logger
    assert "g_entries_attempted" in meta and "g_entries_opened" in meta
