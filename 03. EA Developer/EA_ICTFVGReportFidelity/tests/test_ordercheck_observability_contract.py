import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
PARENT = (
    ROOT.parents[1]
    / "02. AlphaFactory"
    / "runs"
    / "EA_ICTFVGReportFidelity"
    / "20260719_005716"
    / "snapshot"
    / "source"
    / "EA_ICTFVGReportFidelity.mq5"
)
CONTROL_PRESET = ROOT / "presets" / "EURUSD_M5_CONTROL.set"
CHALLENGER_PRESET = ROOT / "presets" / "EURUSD_M5_CHALLENGER.set"


def text(path: Path = SOURCE) -> str:
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def function_body(name: str, source: str | None = None) -> str:
    source = text() if source is None else source
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


def input_lines(source: str) -> list[str]:
    return [line.strip() for line in source.splitlines() if line.startswith("input ")]


def test_child_identity_and_parent_strategy_inputs_are_frozen() -> None:
    current = text()
    parent = text(PARENT)
    assert sha256(PARENT) == "E979C05A57A2C77877CF8CA50620925A4FD7A41DBACD5CD96FE078F452204B82"
    assert (
        'HYPOTHESIS_ID="HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"'
        in current
    )
    inherited = [
        line
        for line in input_lines(current)
        if "InpContext" not in line
        and "InpHuman" not in line
        and "InpFridayFlatten" not in line
    ]
    assert inherited == input_lines(parent)
    assert sha256(CONTROL_PRESET) == "E62D0386B915B4E9BD1FA4A8C761FD72844DBDE2223D175A48F798D6D2F84DB3"
    assert sha256(CHALLENGER_PRESET) == "74FCE7C0C465D5BEA6BAEA9538071C290207621194BA7D74E41996C4CB0A0C68"


def test_ordercheck_uses_boolean_success_and_accepts_zero_retcode() -> None:
    body = function_body("TryOpenTrade")
    assert "bool check_ok=OrderCheck(request,check)" in body
    assert "if(!check_ok)" in body
    assert "check.retcode==0" in body
    assert "g_ordercheck_zero_successes++" in body
    forbidden = (
        "check.retcode!=TRADE_RETCODE_DONE && "
        "check.retcode!=TRADE_RETCODE_PLACED"
    )
    assert forbidden not in body


def test_control_and_execution_rejections_are_separately_observable() -> None:
    source = text()
    required = [
        "g_research_disabled_rejections",
        "g_session_rejections",
        "g_prop_rejections",
        "g_exposure_rejections",
        "g_stop_direction_rejections",
        "g_stop_geometry_rejections",
        "g_volume_rejections",
        "g_ordercheck_rejections",
        "g_ordercheck_zero_successes",
        "g_send_rejections",
    ]
    for counter in required:
        assert counter in source
    run_meta = function_body("WriteRunMeta")
    for counter in required:
        assert counter in run_meta


def test_signal_attrition_is_separately_observable() -> None:
    source = text()
    required = [
        "g_displacement_day_expiries",
        "g_displacement_timeouts",
        "g_retest_day_expiries",
        "g_retest_timeouts",
        "g_retest_stop_breaches",
        "g_retest_invalid_zones",
        "g_retest_depth_rejections",
        "g_retest_candle_rejections",
        "g_adx_read_rejections",
        "g_adx_threshold_rejections",
    ]
    for counter in required:
        assert counter in source
    run_meta = function_body("WriteRunMeta")
    for counter in required:
        assert counter in run_meta
