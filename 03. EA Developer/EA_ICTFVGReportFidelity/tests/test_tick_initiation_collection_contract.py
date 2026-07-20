import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018.mq5"
)
PARENT = (
    ROOT.parents[1]
    / "02. AlphaFactory"
    / "runs"
    / "EA_ICTFVGReportFidelity"
    / "20260719_215636"
    / "snapshot"
    / "source"
    / "EA_ICTFVGReportFidelity.mq5"
)
PLAN = (
    ROOT
    / "research"
    / "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018_COLLECTION_PLAN.md"
)
MATRIX = (
    ROOT
    / "research"
    / "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018_LOGIC_TO_CODE_MATRIX.md"
)
PRESET = ROOT / "presets" / "EURUSD_M5_HYP018_TICK_INIT_COLLECT.set"

PARENT_SHA256 = "FF02340C65CBB0E36B1794CB8263023FDD9B7F9218492E749F1F8875C826A5C6"
PLAN_SHA256 = "E7B4000A45090EC01253AB430867756B3B1623A0A74DFF593E05C4B3B5B471B5"
MATRIX_SHA256 = "85BA86E1F8918A8023204D4525AF147326645B7CF8C615A1E1979AEF54CFF00A"
PRESET_SHA256 = "EE1E6ECFE911A25FA3A919BDF901E50729BE4F3D43F41D32C8578FC0FA79258A"


def sha256(path: Path) -> str:
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


def test_frozen_identity_and_preset() -> None:
    assert sha256(PARENT) == PARENT_SHA256
    assert sha256(PLAN) == PLAN_SHA256
    assert sha256(MATRIX) == MATRIX_SHA256
    assert sha256(PRESET) == PRESET_SHA256
    preset = PRESET.read_text(encoding="utf-8")
    assert "InpResearchAutoMode=false" in preset
    assert "InpEnableTelemetry=true" in preset
    assert "InpSignalMode=4" in preset
    assert "InpMagic=5600728" in preset


def test_source_identity_and_collection_mode_are_explicit() -> None:
    text = source_text()
    assert '#property version   "1.24"' in text
    assert (
        'HYPOTHESIS_ID="HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018"'
        in text
    )
    assert "SIGNAL_TICK_INITIATION_COLLECTION=4" in text
    assert 'return "TICK_INITIATION_COLLECTION"' in function_body("SignalModeName", text)


def test_tick_profile_is_online_closed_interval_and_sign_only() -> None:
    text = source_text()
    for symbol in (
        "struct TickPathProfile",
        "ResetTickPathProfile",
        "AccumulateTickPath",
        "SealTickPathOnNewBar",
        "TickPathImbalance",
        "TickPathSignAgrees",
    ):
        assert symbol in text
    accumulate = function_body("AccumulateTickPath", text)
    assert "tick.bid" in accumulate and "tick.ask" in accumulate
    assert "tick.ask<tick.bid" in accumulate
    assert "mid>profile.last_mid" in accumulate
    assert "mid<profile.last_mid" in accumulate
    assert "MathAbs(mid-profile.last_mid)" in accumulate
    imbalance = function_body("TickPathImbalance", text)
    assert "profile.up_ticks+profile.down_ticks" in imbalance
    assert "profile.up_ticks-profile.down_ticks" in imbalance
    agrees = function_body("TickPathSignAgrees", text)
    assert "direction>0" in agrees and "imbalance>0.0" in agrees
    assert "direction<0" in agrees and "imbalance<0.0" in agrees


def test_first_new_bar_tick_cannot_leak_into_previous_profile() -> None:
    on_tick = function_body("OnTick")
    seal = function_body("SealTickPathOnNewBar")
    assert "SealTickPathOnNewBar(current_bar,tick)" in on_tick
    assert on_tick.index("SealTickPathOnNewBar(current_bar,tick)") < on_tick.index(
        "ProcessClosedM5Bar()"
    )
    assert "g_closed_tick_profile=g_live_tick_profile" in seal
    transition = seal[seal.index("g_closed_tick_profile=g_live_tick_profile") :]
    assert transition.index("g_closed_tick_profile=g_live_tick_profile") < transition.index(
        "ResetTickPathProfile(g_live_tick_profile,current_bar)"
    )
    assert transition.index("ResetTickPathProfile(g_live_tick_profile,current_bar)") < transition.index(
        "AccumulateTickPath(g_live_tick_profile,tick)"
    )


def test_mode_four_logs_confirmation_and_never_opens_order() -> None:
    text = source_text()
    detect = function_body("DetectSweep", text)
    advance = function_body("AdvanceContextState", text)
    process = function_body("ProcessClosedM5Bar", text)
    assert "InpSignalMode==SIGNAL_TICK_INITIATION_COLLECTION" in detect
    assert "InpSignalMode==SIGNAL_TICK_INITIATION_COLLECTION" in process
    marker = "if(InpSignalMode==SIGNAL_TICK_INITIATION_COLLECTION)"
    branch_start = advance.index(marker)
    trade_call = advance.index('TryOpenTrade(setup.direction,stop,"ICTFVG_CONTEXT_STATE")')
    branch = advance[branch_start:trade_call]
    assert "LogTickInitiationDecision" in branch
    assert "ClearSetup(setup)" in branch
    assert "return;" in branch
    assert "TryOpenTrade" not in branch


def test_tick_sidecar_and_funnel_are_auditable() -> None:
    text = source_text()
    open_sidecar = function_body("OpenTickInitiationTelemetry", text)
    log_sidecar = function_body("LogTickInitiationDecision", text)
    run_meta = function_body("WriteRunMeta", text)
    headers = (
        "event_id",
        "confirmation_bar_time",
        "profile_bar_time",
        "direction",
        "valid_ticks",
        "invalid_ticks",
        "up_ticks",
        "down_ticks",
        "flat_ticks",
        "nonzero_ticks",
        "imbalance",
        "sign_agree",
        "path_length",
        "net_mid_change",
        "first_spread",
        "last_spread",
        "max_spread",
        "profile_identity_valid",
    )
    for header in headers:
        assert f'"{header}"' in open_sidecar
    assert "FileWrite(g_tick_initiation_handle" in log_sidecar
    for counter in (
        "g_tick_profiles_logged",
        "g_tick_profiles_defined",
        "g_tick_sign_agree",
        "g_tick_sign_nonagree",
        "g_tick_profile_identity_invalid",
    ):
        assert counter in text
        assert counter in run_meta


def test_collection_sidecar_closes_and_run_meta_declares_schema() -> None:
    text = source_text()
    init = function_body("OpenLifecycleTelemetry", text)
    deinit = function_body("OnDeinit", text)
    run_meta = function_body("WriteRunMeta", text)
    assert "OpenTickInitiationTelemetry()" in init
    assert "g_tick_initiation_handle" in deinit
    assert "tick_initiation_schema" in run_meta
    assert "tick-initiation-v1" in run_meta
