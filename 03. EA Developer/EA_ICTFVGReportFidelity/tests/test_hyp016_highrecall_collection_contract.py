import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1.mq5"
)
PLAN = (
    ROOT
    / "research"
    / "HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1_COLLECTION_PLAN_V2.md"
)
PRESET = ROOT / "presets" / "EURUSD_M5_HYP016_HIGHRECALL_CONTEXT_COLLECT.set"
PARENT_SHA256 = "5915632D4CE97783F27A28E009F97D064D40748FBB0A376BD25F31BEC3658F20"
PLAN_SHA256 = "B6BB22A945292459FA134663FA94E9330CA86E5F2D2C0290BF2AA0931299BA47"
PRESET_SHA256 = "353C06AC6B631E1FB6E131BD91C68FC4E94DCAF7794F2C976CFCFDBC2E55264C"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def function_body(name: str, source: str) -> str:
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
    raise AssertionError(name)


def test_plan_and_collection_preset_are_frozen_pre_run() -> None:
    assert sha256(PLAN) == PLAN_SHA256
    assert sha256(PRESET) == PRESET_SHA256
    preset = PRESET.read_text(encoding="utf-8")
    assert "InpResearchAutoMode=false" in preset
    assert "InpEnableTelemetry=true" in preset
    assert "InpSignalMode=0" in preset
    assert "InpRequireNewsGuard=false" in preset


def test_hyp016r1_source_change_is_identity_and_telemetry_metadata_only() -> None:
    current = source_text()
    assert '#property version   "1.22"' in current
    assert (
        'HYPOTHESIS_ID="HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1"'
        in current
    )
    assert 'TELEMETRY_PROFILE="lifecycle-v3"' in current
    normalized = current.replace('#property version   "1.22"', '#property version   "1.21"')
    normalized = normalized.replace(
        'HYPOTHESIS_ID="HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1"',
        'HYPOTHESIS_ID="HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016"',
    )
    normalized = normalized.replace(
        'TELEMETRY_PROFILE="lifecycle-v3"',
        'TELEMETRY_PROFILE="lifecycle-v3+human-context-v1"',
    )
    assert hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper() == PARENT_SHA256


def test_collection_logger_precedes_research_disabled_trade_veto() -> None:
    current = source_text()
    detect_start = current.index("void DetectSweep(")
    detect_end = current.index("void AdvanceContextState(", detect_start)
    detect = current[detect_start:detect_end]
    assert detect.index("LogHumanContextDecision(") < detect.index("TryOpenTrade(")
    can_open = function_body("CanOpenNow", current)
    assert "if(!InpResearchAutoMode)" in can_open
    assert "g_research_disabled_rejections++" in can_open
