import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022.mq5"
)
PARENT = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018.mq5"
)
PLAN = ROOT / "research" / "HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022_COLLECTION_PLAN.md"
MATRIX = ROOT / "research" / "HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022_LOGIC_TO_CODE_MATRIX.md"
PRESET = ROOT / "presets" / "EURUSD_M5_HYP022_REPEATED_CHURN_COLLECT.set"

PARENT_SHA = "41536FFC43BE85B1250A627197BD63FED5C7D5C7CF87D8965163F5449EACDA40"
PLAN_SHA = "1A909F222AA22BB39730E2017081524B84EA2B7BEB3D8E1DBD3D0DF9FAED2B67"
MATRIX_SHA = "C3C54C46407A0674EBD428CFC7C6B89C836353F39F862F0BCCACB7F785DEA431"
PRESET_SHA = "2C55F4C6EE8E1A150B921A1C5D51F953E8434639EB967B70A70A006305A551EA"


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


def reentries(level: float, direction: int, mids: list[float]) -> int:
    side = 0
    first_favorable = False
    count = 0
    for mid in mids:
        distance = direction * (mid - level)
        next_side = 1 if distance > 0 else -1 if distance < 0 else side
        if next_side == 0:
            continue
        if next_side == 1 and not first_favorable:
            first_favorable = True
        if first_favorable and side == 1 and next_side == -1:
            count += 1
        side = next_side
    return count


def label(count: int) -> str:
    return "ORDERLY" if count <= 1 else "REPEATED_CHURN"


def test_frozen_parent_plan_matrix_and_preset() -> None:
    assert sha(PARENT) == PARENT_SHA
    assert sha(PLAN) == PLAN_SHA
    assert sha(MATRIX) == MATRIX_SHA
    assert sha(PRESET) == PRESET_SHA
    preset = PRESET.read_text(encoding="utf-8")
    assert "InpSignalMode=5" in preset
    assert "InpMagic=5600731" in preset
    assert "InpResearchAutoMode=false" in preset


def test_identical_ohlc_paths_prove_repeated_multiplicity_is_new() -> None:
    orderly = [101.0, 110.0, 99.0, 109.0]
    repeated = [101.0, 99.0, 105.0, 99.0, 110.0, 109.0]
    ohlc = lambda path: (path[0], max(path), min(path), path[-1])
    assert ohlc(orderly) == ohlc(repeated) == (101.0, 110.0, 99.0, 109.0)
    assert reentries(100.0, 1, orderly) == 1
    assert reentries(100.0, 1, repeated) == 2
    assert label(reentries(100.0, 1, orderly)) == "ORDERLY"
    assert label(reentries(100.0, 1, repeated)) == "REPEATED_CHURN"


def test_killed_hyp020_any_recross_bit_collapses_to_ohlc_pierce() -> None:
    no_pierce = [101.0, 110.0, 100.1, 109.0]
    pierce_once = [101.0, 110.0, 99.0, 109.0]
    assert reentries(100.0, 1, no_pierce) == 0
    assert reentries(100.0, 1, pierce_once) == 1
    assert min(no_pierce) >= 100.0
    assert min(pierce_once) < 100.0


def test_source_identity_mode_and_slot_owned_state_are_explicit() -> None:
    text = source_text()
    assert '#property version   "1.25"' in text
    assert 'HYPOTHESIS_ID="HYP-ICT-FVG-REPEATED-LEVEL-CHURN-COLLECT-EURUSD-M5-022"' in text
    assert "SIGNAL_REPEATED_LEVEL_CHURN_COLLECTION=5" in text
    assert 'return "REPEATED_LEVEL_CHURN_COLLECTION"' in function_body("SignalModeName", text)
    for field in (
        "slot_index", "level_path_active", "level_path_level",
        "level_path_start_time", "level_path_last_tick_time", "level_path_side",
        "level_path_first_favorable", "level_path_first_favorable_time",
        "level_path_valid_ticks", "level_path_invalid_ticks",
        "level_path_adverse_reentries",
    ):
        assert field in text


def test_online_accumulator_counts_only_favorable_to_adverse_transitions() -> None:
    text = source_text()
    body = function_body("AccumulateSetupLevelPath", text)
    assert "tick.bid" in body and "tick.ask" in body
    assert "tick.ask<tick.bid" in body
    assert "setup.direction*(mid-setup.level_path_level)" in body
    assert "next_side=setup.level_path_side" in body
    assert "setup.level_path_side==1 && next_side==-1" in body
    assert "setup.level_path_adverse_reentries++" in body
    assert "setup.level_path_first_favorable=true" in body


def test_active_slot_registry_is_compacted_and_setup_owned() -> None:
    text = source_text()
    register = function_body("RegisterActiveLevelPathSlot", text)
    accumulate = function_body("AccumulateActiveLevelPaths", text)
    clear = function_body("ClearSetup", text)
    assert "g_active_level_path_indices" in register
    assert "g_level_path_slot_active" in register
    assert "write_index" in accumulate
    assert "g_setups[slot]" in accumulate
    assert "g_active_level_path_count=write_index" in accumulate
    assert "g_level_path_slot_active[slot]=false" in clear


def test_new_bar_order_excludes_post_confirmation_tick() -> None:
    body = function_body("OnTick")
    assert body.index("SealTickPathOnNewBar(current_bar,tick)") < body.index("ProcessClosedM5Bar()")
    new_bar_tail = body[body.index("g_last_m5_bar=current_bar;") :]
    assert new_bar_tail.index("ProcessClosedM5Bar()") < new_bar_tail.index("AccumulateActiveLevelPaths(tick)")
    same_bar_branch = body[body.index("if(current_bar==g_last_m5_bar)") : body.index("g_last_m5_bar=current_bar;")]
    assert "AccumulateActiveLevelPaths(tick)" in same_bar_branch
    assert "return;" in same_bar_branch


def test_mode_five_logs_level_path_and_cannot_open_order() -> None:
    text = source_text()
    advance = function_body("AdvanceContextState", text)
    detect = function_body("DetectSweep", text)
    process = function_body("ProcessClosedM5Bar", text)
    marker = "if(InpSignalMode==SIGNAL_REPEATED_LEVEL_CHURN_COLLECTION)"
    start = advance.index(marker)
    trade = advance.index('TryOpenTrade(setup.direction,stop,"ICTFVG_CONTEXT_STATE")')
    branch = advance[start:trade]
    assert marker in detect and marker in process
    assert "LogLevelPathDecision" in branch
    assert "ClearSetup(setup)" in branch and "return;" in branch
    assert "TryOpenTrade" not in branch


def test_level_path_sidecar_and_runmeta_are_auditable() -> None:
    text = source_text()
    opener = function_body("OpenLevelPathTelemetry", text)
    logger = function_body("LogLevelPathDecision", text)
    meta = function_body("WriteRunMeta", text)
    for header in (
        "event_id", "decision_time", "sweep_time", "confirmation_bar_time",
        "direction", "level", "interval_start_time", "last_tick_time",
        "valid_ticks", "invalid_ticks", "first_favorable_time",
        "adverse_reentry_count", "path_label", "side_at_seal",
        "interval_identity_valid", "tick_provenance",
    ):
        assert f'"{header}"' in opener
    assert '"ORDERLY"' in logger and '"REPEATED_CHURN"' in logger
    assert "setup.level_path_adverse_reentries<=1" in logger
    for counter in (
        "g_level_paths_logged", "g_level_paths_defined", "g_level_paths_orderly",
        "g_level_paths_repeated_churn", "g_level_path_identity_invalid",
    ):
        assert counter in meta


def test_level_sidecar_is_opened_and_closed() -> None:
    text = source_text()
    init = function_body("OpenLifecycleTelemetry", text)
    deinit = function_body("OnDeinit", text)
    assert "OpenLevelPathTelemetry()" in init
    assert "g_level_path_handle" in deinit
    assert "level-path-v1" in function_body("WriteRunMeta", text)
