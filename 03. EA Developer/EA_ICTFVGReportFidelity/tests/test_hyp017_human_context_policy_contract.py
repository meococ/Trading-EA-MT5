import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT.parents[1]
    / "02. AlphaFactory"
    / "runs"
    / "EA_ICTFVGReportFidelity"
    / "20260719_215636"
    / "snapshot"
    / "source"
    / "EA_ICTFVGReportFidelity.mq5"
)
PLAN = ROOT / "research" / "HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017_MODEL0_PLAN.md"
PRESET = ROOT / "presets" / "EURUSD_M5_HYP017_HUMAN_CONTEXT_POLICY.set"
PLAN_SHA256 = "0FF4BABC96257BAC7B70F2A017320832F25CC53546868946F7F3E235B8392FF2"
PRESET_SHA256 = "AA97D48D9999EF6303B8E9849BEF87FDAA399BCAF4A106E4574073BBEBF74EEC"


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


def test_hyp017_plan_and_single_run_preset_are_frozen() -> None:
    assert sha256(PLAN) == PLAN_SHA256
    assert sha256(PRESET) == PRESET_SHA256
    preset = PRESET.read_text(encoding="utf-8")
    assert "InpResearchAutoMode=true" in preset
    assert "InpSignalMode=3" in preset
    assert "InpRiskPercent=0.01" in preset
    assert "InpMaxAccountDrawdownPct=100.00" in preset
    assert "InpMagic=5600727" in preset


def test_hyp017_identity_and_policy_mode_are_explicit() -> None:
    source = source_text()
    assert '#property version   "1.23"' in source
    assert (
        'HYPOTHESIS_ID="HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017"'
        in source
    )
    assert "SIGNAL_HUMAN_CONTEXT_POLICY=3" in source
    assert 'return "HUMAN_CONTEXT_POLICY"' in function_body("SignalModeName", source)


def test_policy_uses_the_same_snapshot_that_is_logged() -> None:
    source = source_text()
    logger = function_body("LogHumanContextDecision", source)
    detect = function_body("DetectSweep", source)
    assert "bool LogHumanContextDecision(" in source
    assert "BuildHumanContextSnapshot(" in logger
    assert "HUMAN_CONTEXT_EXTERNAL_SWEEP_WITH_ROOM" in logger
    assert "HUMAN_CONTEXT_INTERNAL_SWEEP_WITH_ROOM" in logger
    assert "return policy_accept;" in logger
    assert "SIGNAL_HUMAN_CONTEXT_POLICY" in detect
    assert "bool policy_accept=LogHumanContextDecision(" in detect
    assert "if(!policy_accept)" in detect
    assert 'TryOpenTrade(direction,stop,"ICTFVG_HUMAN_CONTEXT_POLICY")' in detect
    assert detect.index("LogHumanContextDecision(") < detect.index("TryOpenTrade(")


def test_server_clock_uses_frozen_era_hybrid_dst_model() -> None:
    source = source_text()
    server_to_utc = function_body("ServerToUtc", source)
    broker_dst = function_body("IsBrokerDstServerTime", source)
    us_dst = function_body("IsUsDstServerTime", source)
    assert "parts.year>=2024" in broker_dst
    assert "IsUsDstServerTime(server_time)" in broker_dst
    assert "IsEuropeDstServerTime(server_time)" in broker_dst
    assert "NthSunday(parts.year,3,2,7)" in us_dst
    assert "NthSunday(parts.year,11,1,6)" in us_dst
    assert "server_time-InpServerUtcOffsetWinterHours*3600" in us_dst
    assert "IsBrokerDstServerTime(server_time)" in server_to_utc
