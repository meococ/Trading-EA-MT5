import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
PLAN_V2 = (
    ROOT
    / "research"
    / "HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012_MODEL0_PLAN_V2.md"
)
CONTROL = ROOT / "presets" / "EURUSD_M5_CONTEXT_CONTROL_2018YTD.set"
CHALLENGER = ROOT / "presets" / "EURUSD_M5_CONTEXT_CHALLENGER_2018YTD.set"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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


def preset(path: Path) -> dict[str, str]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            rows[key] = value
    return rows


def test_prereg_and_matched_presets_are_frozen() -> None:
    assert sha256(PLAN_V2) == (
        "8A50C07039C5FE2725E7CAEB29637F509773646EDEE926185BD3B308C291FDF3"
    )
    assert sha256(CONTROL) == (
        "9FC1B200E66D76309F130205B9D825B63B398C4C056541A33AE0896618FDE6D2"
    )
    assert sha256(CHALLENGER) == (
        "7230C264DE07095CB26E6404C1B12E4A6C8D5D70AFF46384FF4CC5D4F1958E8E"
    )
    control = preset(CONTROL)
    challenger = preset(CHALLENGER)
    differences = {
        key: (control.get(key), challenger.get(key))
        for key in control.keys() | challenger.keys()
        if control.get(key) != challenger.get(key)
    }
    assert differences == {
        "InpSignalMode": ("0", "2"),
        "InpMagic": ("5600722", "5600723"),
    }


def test_current_observation_child_preserves_context_mode() -> None:
    text = source_text()
    assert (
        'HYPOTHESIS_ID="HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"'
        in text
    )
    assert "SIGNAL_CONTEXT_STATE=2" in text
    assert "InpContextMaxBars=3" in text
    assert "InpContextBodyMultiple=1.00" in text
    assert "InpContextCloseFraction=0.25" in text


def test_context_state_is_bounded_and_closed_bar_confirmed() -> None:
    text = source_text()
    detect = function_body("DetectSweep", text)
    advance = function_body("AdvanceContextState", text)
    process = function_body("ProcessClosedM5Bar", text)
    assert "ContextSetupExists" in detect
    assert "AddSweepSetup" in detect
    assert "setup.bars_in_stage>InpContextMaxBars" in advance
    assert "bars[0].time<=setup.sweep_time" in advance
    assert "bars[0].close<=setup.sweep_low" in advance
    assert "bars[0].close>=setup.sweep_high" in advance
    assert "body>=InpContextBodyMultiple*mean_body" in advance
    assert "bars[0].close>setup.sweep_high" in advance
    assert "bars[0].close<setup.sweep_low" in advance
    assert "close_location>=1.0-InpContextCloseFraction" in advance
    assert "close_location<=InpContextCloseFraction" in advance
    assert 'TryOpenTrade(setup.direction,stop,"ICTFVG_CONTEXT_STATE")' in advance
    assert "InpSignalMode==SIGNAL_CONTEXT_STATE" in process
    assert "CopyRates(_Symbol,PERIOD_M5,1," in process
    assert "CopyRates(_Symbol,PERIOD_M5,0," not in process


def test_context_funnel_is_observable() -> None:
    text = source_text()
    run_meta = function_body("WriteRunMeta", text)
    required = [
        "g_context_duplicate_rejections",
        "g_context_acceptance_invalidations",
        "g_context_timeouts",
        "g_context_confirmations",
    ]
    for counter in required:
        assert counter in text
        assert counter in run_meta


def test_context_inputs_fail_closed() -> None:
    body = function_body("ValidateInputs")
    assert "InpContextMaxBars<1" in body
    assert "InpContextBodyMultiple<=0.0" in body
    assert "InpContextCloseFraction<=0.0" in body
    assert "InpContextCloseFraction>=0.5" in body
