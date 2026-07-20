import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
ENGINE = ROOT / "HumanContextEngine.mqh"
REFERENCE = ROOT / "research" / "build_hyp015_human_context_reference.py"
PLAN = (
    ROOT
    / "research"
    / "HYP-ICT-FVG-HUMAN-CONTEXT-ENGINE-EURUSD-M5-015_ENGINEERING_PLAN.md"
)
PARENT = (
    ROOT
    / "research"
    / "source_snapshots"
    / "EA_ICTFVGReportFidelity_HYP-ICT-FVG-FRIDAY-SAFE-EURUSD-M5-013.mq5"
)
PARENT_SHA256 = "1E04144A5E26651B993E7A13202FC85B8D5C0AB3FD7C8FAA5D890897E3B4B196"
PLAN_SHA256 = "72D58A4D1EABB43F6188B38E1835E2562E5434FF84166FC625BA1EFBBFCD7799"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def function_body(name: str, source: str) -> str:
    match = re.search(
        rf"(?:bool|int|double|datetime|string|void)\s+{name}\s*\(", source
    )
    assert match is not None, name
    opening = source.index("{", match.end())
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
    raise AssertionError(f"unterminated function: {name}")


def test_frozen_parent_and_plan_are_bound_before_source_change() -> None:
    assert sha256(PARENT) == PARENT_SHA256
    assert sha256(PLAN) == PLAN_SHA256


def test_current_child_retains_the_package_local_hyp015_engine() -> None:
    source = text(SOURCE)
    assert '#property version   "1.27"' in source
    assert (
        'HYPOTHESIS_ID="HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"'
        in source
    )
    assert '#include "HumanContextEngine.mqh"' in source
    assert ENGINE.is_file()


def test_engine_exposes_the_frozen_human_context_schema() -> None:
    engine = text(ENGINE)
    for state in (
        "HUMAN_CONTEXT_INCOMPLETE",
        "HUMAN_CONTEXT_NO_DIRECTIONAL_TARGET",
        "HUMAN_CONTEXT_DIRECTIONAL_EXHAUSTION",
        "HUMAN_CONTEXT_STRUCTURE_CONFLICT",
        "HUMAN_CONTEXT_EXTERNAL_SWEEP_WITH_ROOM",
        "HUMAN_CONTEXT_INTERNAL_SWEEP_WITH_ROOM",
        "HUMAN_CONTEXT_INSUFFICIENT_ROOM",
    ):
        assert state in engine
    for field in (
        "h1_range_location",
        "h4_range_location",
        "h1_structure",
        "h4_structure",
        "previous_day_high",
        "previous_day_low",
        "previous_week_high",
        "previous_week_low",
        "asia_high",
        "asia_low",
        "nearest_pool_type",
        "nearest_pool_price",
        "directional_pool_count",
        "room_r",
        "external_sweep",
        "external_swept_count",
        "partial_h1_body_atr",
        "partial_h4_body_atr",
        "confirmation_body_atr",
        "directional_run_bars",
        "h1_extension_atr",
        "h4_extension_atr",
        "spread_to_risk",
    ):
        assert field in engine


def test_all_htf_and_partial_context_reads_are_closed_bar_only() -> None:
    engine = text(ENGINE)
    assert "CopyRates(_Symbol,PERIOD_H1,1," in engine
    assert "CopyRates(_Symbol,PERIOD_H4,1," in engine
    assert "CopyRates(_Symbol,PERIOD_D1,1," in engine
    assert "CopyRates(_Symbol,PERIOD_W1,1," in engine
    assert "CopyRates(_Symbol,PERIOD_M5,1," in engine
    assert not re.search(r"CopyRates\([^\n]*PERIOD_(?:H1|H4|D1|W1),0,", engine)
    assert "BuildPartialHtfFromClosedM5" in engine


def test_context_is_logged_before_send_and_cannot_change_the_trade_policy() -> None:
    source = text(SOURCE)
    expected = {
        "DetectSweep": "ICTFVG_CONTROL_SWEEP",
        "AdvanceContextState": "ICTFVG_CONTEXT_STATE",
        "AdvanceRetest": "ICTFVG_FULL_FIDELITY",
    }
    for function, reason in expected.items():
        body = function_body(function, source)
        log_at = body.index(f'LogHumanContextDecision(')
        send_at = body.index(f'TryOpenTrade', log_at)
        reason_at = body.index(reason)
        assert log_at <= reason_at < send_at
    logger = function_body("LogHumanContextDecision", source)
    assert "BuildHumanContextSnapshot" in logger
    assert "FileWrite" in logger
    assert "event_sequence=g_human_context_snapshots+g_human_context_invalid" in logger
    assert '"%s_%I64d_%s_%d_%I64d"' in logger
    assert "TryOpenTrade" not in logger
    assert "return policy_accept;" in logger


def test_decision_telemetry_is_outcome_blind_and_separate_from_lifecycle() -> None:
    source = text(SOURCE)
    opener = function_body("OpenHumanContextTelemetry", source)
    lowered = opener.lower()
    assert "g_human_context_handle" in opener
    assert "g_telemetry_handle" not in opener
    for forbidden in ("exit", "pnl", "profit", "commission", "mfe", "mae"):
        assert forbidden not in lowered


def test_reference_builder_is_explicitly_outcome_blind() -> None:
    reference = text(REFERENCE)
    assert "ALLOWED_POSITION_COLUMNS" in reference
    assert "FORBIDDEN_OUTCOME_COLUMNS" in reference
    assert "required_reference_rows" in reference
    assert "3385" in reference
    assert "range_position_20" in reference
    for forbidden in ("net_r", "profit", "deal_net", "mfe", "mae"):
        assert forbidden not in re.search(
            r"ALLOWED_POSITION_COLUMNS\s*=\s*\((.*?)\)", reference, re.S
        ).group(1).lower()
