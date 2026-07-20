import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
PARENT = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022.mq5"
)
HYP024_SNAPSHOT = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024.mq5"
)
PLAN = ROOT / "research" / "HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024_COLLECTION_PLAN.md"
MATRIX = ROOT / "research" / "HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024_LOGIC_TO_CODE_MATRIX.md"
PRESET = ROOT / "presets" / "EURUSD_M5_HYP024_TIME_RESILIENCE_COLLECT.set"

PARENT_SHA = "5FF5F8600362C95DAC66C2F1450A2B82D4E1B202F98679B9BE0C52C71039410C"
PLAN_SHA = "6A80E4C97D19D901F6D96112114B0979F5065323E307D5907620FC77906E8269"
MATRIX_SHA = "9BBE43380CFC24A35101A6CEBEE559572EAC6B97467E37853570EEEC667847E8"
PRESET_SHA = "7192B0BC4963C8593B7F1C84D5D370EAC5EC45DEB28D7DBCAB4112649297A6BE"


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


def reentries(level: float, direction: int, observations: list[tuple[int, float]]) -> int:
    side = 0
    first_favorable = False
    count = 0
    for _, mid in observations:
        directed = direction * (mid - level)
        next_side = 1 if directed > 0 else -1 if directed < 0 else side
        if next_side == 1 and not first_favorable:
            first_favorable = True
        if first_favorable and side == 1 and next_side == -1:
            count += 1
        if next_side != 0:
            side = next_side
    return count


def test_frozen_parent_plan_matrix_and_preset() -> None:
    assert sha(PARENT) == PARENT_SHA
    assert sha(PLAN) == PLAN_SHA
    assert sha(MATRIX) == MATRIX_SHA
    assert sha(PRESET) == PRESET_SHA
    preset = PRESET.read_text(encoding="utf-8")
    assert "InpSignalMode=6" in preset
    assert "InpMagic=5600733" in preset
    assert "InpResearchAutoMode=false" in preset


def test_same_ohlc_prices_and_reentry_count_can_flip_duration_label() -> None:
    path_a = [(0, 101.0), (1, 99.0), (9, 109.0)]
    path_b = [(0, 101.0), (8, 99.0), (9, 109.0)]
    ohlc = lambda path: (path[0][1], max(p for _, p in path), min(p for _, p in path), path[-1][1])
    assert ohlc(path_a) == ohlc(path_b) == (101.0, 109.0, 99.0, 109.0)
    assert [p for _, p in path_a] == [p for _, p in path_b]
    assert reentries(100.0, 1, path_a) == reentries(100.0, 1, path_b) == 1
    assert integrate(100.0, 1, path_a, 10) == (2, 8, "ADVERSE_DOMINANT")
    assert integrate(100.0, 1, path_b, 10) == (9, 1, "FAVORABLE_DOMINANT")


def test_equality_credits_elapsed_time_but_keeps_previous_side() -> None:
    observations = [(0, 101.0), (3, 100.0), (6, 99.0)]
    assert integrate(100.0, 1, observations, 10) == (6, 4, "FAVORABLE_DOMINANT")


def test_invalid_quote_does_not_advance_clock_or_change_side() -> None:
    observations = [(0, 101.0), (2, None), (5, 99.0)]
    assert integrate(100.0, 1, observations, 10) == (5, 5, "UNDEFINED")


def test_never_favorable_and_exact_duration_tie_are_undefined() -> None:
    assert integrate(100.0, 1, [(0, 99.0), (5, 98.0)], 10) == (0, 0, "UNDEFINED")
    assert integrate(100.0, 1, [(0, 101.0), (5, 99.0)], 10) == (5, 5, "UNDEFINED")


def test_source_identity_mode_and_millisecond_slot_state_are_explicit() -> None:
    text = source_text()
    historical = HYP024_SNAPSHOT.read_text(encoding="utf-8")
    assert '#property version   "1.26"' in historical
    assert 'HYPOTHESIS_ID="HYP-ICT-FVG-TIME-WEIGHTED-LEVEL-RESILIENCE-COLLECT-EURUSD-M5-024"' in historical
    assert '#property version   "1.27"' in text
    assert 'HYPOTHESIS_ID="HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"' in text
    assert "SIGNAL_TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION=6" in text
    assert 'return "TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION"' in function_body("SignalModeName", text)
    for field in (
        "resilience_active", "resilience_level", "resilience_start_msc",
        "resilience_last_valid_msc", "resilience_side", "resilience_first_favorable",
        "resilience_first_favorable_msc", "resilience_favorable_ms",
        "resilience_adverse_ms", "resilience_max_gap_ms", "resilience_valid_ticks",
        "resilience_invalid_ticks",
    ):
        assert field in text


def test_online_accumulator_uses_time_msc_and_last_side_carry() -> None:
    text = source_text()
    body = function_body("AccumulateSetupResilience", text)
    assert "tick.time_msc" in body
    assert "tick.bid" in body and "tick.ask" in body and "tick.ask<tick.bid" in body
    assert "setup.direction*(mid-setup.resilience_level)" in body
    assert "tick.time_msc-setup.resilience_last_valid_msc" in body
    assert "setup.resilience_favorable_ms+=delta_msc" in body
    assert "setup.resilience_adverse_ms+=delta_msc" in body
    assert "next_side=setup.resilience_side" in body
    assert "setup.resilience_last_valid_msc=tick.time_msc" in body


def test_resilience_registry_is_separate_compacted_and_setup_owned() -> None:
    text = source_text()
    register = function_body("RegisterActiveResilienceSlot", text)
    accumulate = function_body("AccumulateActiveResilience", text)
    clear = function_body("ClearSetup", text)
    assert "g_active_resilience_indices" in register
    assert "g_resilience_slot_active" in register
    assert "write_index" in accumulate and "g_setups[slot]" in accumulate
    assert "g_active_resilience_count=write_index" in accumulate
    assert "g_resilience_slot_active[slot]=false" in clear


def test_new_bar_order_excludes_post_confirmation_tick() -> None:
    body = function_body("OnTick")
    assert body.index("ProcessClosedM5Bar()") < body.rindex("AccumulateActiveResilience(tick)")
    same_bar = body[body.index("if(current_bar==g_last_m5_bar)") : body.index("g_last_m5_bar=current_bar;")]
    assert "AccumulateActiveResilience(tick)" in same_bar
    assert "return;" in same_bar


def test_mode_six_logs_resilience_and_cannot_open_order() -> None:
    text = source_text()
    advance = function_body("AdvanceContextState", text)
    detect = function_body("DetectSweep", text)
    process = function_body("ProcessClosedM5Bar", text)
    marker = "if(InpSignalMode==SIGNAL_TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION)"
    start = advance.index(marker)
    trade = advance.index('TryOpenTrade(setup.direction,stop,"ICTFVG_CONTEXT_STATE")')
    branch = advance[start:trade]
    assert marker in detect and marker in process
    assert "LogLevelResilienceDecision" in branch
    assert "ClearSetup(setup)" in branch and "return;" in branch
    assert "TryOpenTrade" not in branch


def test_sidecar_and_runmeta_expose_auditable_duration_fields() -> None:
    text = source_text()
    opener = function_body("OpenLevelResilienceTelemetry", text)
    logger = function_body("LogLevelResilienceDecision", text)
    meta = function_body("WriteRunMeta", text)
    for header in (
        "event_id", "decision_time", "decision_msc", "sweep_time",
        "confirmation_bar_time", "direction", "level", "interval_start_msc",
        "last_valid_msc", "valid_ticks", "invalid_ticks", "first_favorable_msc",
        "favorable_ms", "adverse_ms", "total_ms", "max_gap_ms",
        "resilience_label", "side_at_seal", "interval_identity_valid",
        "duration_identity_valid", "tick_provenance",
    ):
        assert f'"{header}"' in opener
    assert '"FAVORABLE_DOMINANT"' in logger and '"ADVERSE_DOMINANT"' in logger
    assert "setup.resilience_favorable_ms>setup.resilience_adverse_ms" in logger
    assert "decision_msc-setup.resilience_last_valid_msc" in logger
    for counter in (
        "g_resilience_logged", "g_resilience_defined", "g_resilience_favorable_dominant",
        "g_resilience_adverse_dominant", "g_resilience_identity_invalid",
        "g_resilience_duration_invalid",
    ):
        assert counter in meta


def test_resilience_sidecar_is_opened_and_closed() -> None:
    text = source_text()
    init = function_body("OpenLifecycleTelemetry", text)
    deinit = function_body("OnDeinit", text)
    assert "OpenLevelResilienceTelemetry()" in init
    assert "g_level_resilience_handle" in deinit
    assert "level-resilience-v1" in function_body("WriteRunMeta", text)
