import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
PARENT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "runs"
    / "EA_ICTFVGReportFidelity"
    / "20260719_162104"
    / "snapshot"
    / "source"
    / "EA_ICTFVGReportFidelity.mq5"
)
PARENT_SHA256 = "8B1C9E283B97716C91F61FCDB2A74B6168CC0671DAE896A941F0F181674E6CE1"


def source_text(path: Path = SOURCE) -> str:
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def function_body(name: str, text: str | None = None) -> str:
    text = source_text() if text is None else text
    match = re.search(rf"(?:bool|int|double|datetime|string|void)\s+{name}\s*\(", text)
    assert match is not None, name
    opening = text.index("{", match.end())
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening : index + 1]
    raise AssertionError(f"unterminated function: {name}")


def without_hyp015_observation_calls(body: str) -> str:
    body = re.sub(
        r"\n\s*LogHumanContextDecision\([\s\S]*?\"ICTFVG_[A-Z_]+\"\);",
        "",
        body,
    )
    body = re.sub(
        r"\n\s*if\(InpSignalMode==SIGNAL_TICK_INITIATION_COLLECTION\)\s*"
        r"\{\s*LogTickInitiationDecision\(setup.direction,bars\[0\]\);\s*"
        r"ClearSetup\(setup\);\s*return;\s*\}",
        "",
        body,
    )
    body = re.sub(
        r"\s*\|\|\s*InpSignalMode==SIGNAL_TICK_INITIATION_COLLECTION",
        "",
        body,
    )
    body = re.sub(
        r"\n\s*if\(InpSignalMode==SIGNAL_REPEATED_LEVEL_CHURN_COLLECTION\)\s*"
        r"\{\s*LogLevelPathDecision\(setup,bars\[0\]\);\s*"
        r"ClearSetup\(setup\);\s*return;\s*\}",
        "",
        body,
    )
    body = re.sub(
        r"\n\s*if\(InpSignalMode==SIGNAL_TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION\)\s*"
        r"\{\s*LogLevelResilienceDecision\(setup,bars\[0\]\);\s*"
        r"ClearSetup\(setup\);\s*return;\s*\}",
        "",
        body,
    )
    body = re.sub(
        r"\n\s*if\(InpSignalMode==SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION\)\s*"
        r"\{\s*LogLevelResilienceDecision\(setup,bars\[0\]\);\s*"
        r"ClearSetup\(setup\);\s*return;\s*\}",
        "",
        body,
    )
    body = re.sub(
        r"\n\s*if\(InpSignalMode==SIGNAL_TIME_WEIGHTED_LEVEL_RESILIENCE_COLLECTION\)\s*"
        r"context_collection_mode=true;",
        "",
        body,
    )
    body = re.sub(
        r"\n\s*if\(InpSignalMode==SIGNAL_PIVOT_RECLAIM_DWELL_COLLECTION\)\s*"
        r"context_collection_mode=true;",
        "",
        body,
    )
    body = re.sub(
        r"\n\s*else\s*\{\s*"
        r"bool context_collection_mode=\(InpSignalMode==SIGNAL_CONTEXT_STATE\);\s*"
        r"if\(InpSignalMode==SIGNAL_REPEATED_LEVEL_CHURN_COLLECTION\)\s*"
        r"context_collection_mode=true;\s*"
        r"if\(context_collection_mode\)\s*"
        r"AdvanceContextSetups\(bars,copied,date_key\);\s*\}",
        "\n   else if(InpSignalMode==SIGNAL_CONTEXT_STATE)\n"
        "      AdvanceContextSetups(bars,copied,date_key);",
        body,
    )
    return body


def test_parent_snapshot_is_the_frozen_hyp012_source() -> None:
    assert PARENT.is_file()
    assert sha256(PARENT) == PARENT_SHA256


def test_friday_cutoff_is_explicitly_frozen_at_2055_utc() -> None:
    text = source_text()
    assert "input int              InpFridayFlattenUtcHour=20;" in text
    assert "input int              InpFridayFlattenUtcMinute=55;" in text
    cutoff = function_body("FridayCutoffReached", text)
    assert "TimeToStruct(ServerToUtc(server_time),parts)" in cutoff
    assert "parts.day_of_week!=5" in cutoff
    assert "InpFridayFlattenUtcHour*60+InpFridayFlattenUtcMinute" in cutoff


def test_friday_cutoff_vetoes_entries_and_precedes_stop_management() -> None:
    can_open = function_body("CanOpenNow")
    manage = function_body("ManageOwnedPosition")
    on_tick = function_body("OnTick")
    assert "FridayCutoffReached(server_time)" in can_open
    cutoff_index = manage.index("FridayCutoffReached(now)")
    stop_index = manage.index("InpBreakEvenTriggerR")
    assert cutoff_index < stop_index
    assert manage.index("trade.PositionClose(ticket)") < stop_index
    assert on_tick.index("ManageOwnedPosition();") < on_tick.index("ProcessClosedM5Bar();")


def test_friday_inputs_fail_closed_and_signal_geometry_is_unchanged() -> None:
    validate = function_body("ValidateInputs")
    assert "InpFridayFlattenUtcHour<18" in validate
    assert "InpFridayFlattenUtcHour>21" in validate
    assert "InpFridayFlattenUtcMinute<0" in validate
    assert "InpFridayFlattenUtcMinute>59" in validate

    parent_text = source_text(PARENT)
    current_text = source_text()
    for name in (
            "AdvanceContextState",
        "ProcessClosedM5Bar",
        "RiskSizedVolume",
        "StopGeometryValid",
    ):
        assert without_hyp015_observation_calls(
            function_body(name, current_text)
        ) == function_body(name, parent_text), name
