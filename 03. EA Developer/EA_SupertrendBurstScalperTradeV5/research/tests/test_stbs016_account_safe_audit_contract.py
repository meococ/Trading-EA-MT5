from __future__ import annotations

import math
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV5.mq5"
V4_SOURCE = PACKAGE.parent / "EA_SupertrendBurstScalperTradeV4" / "EA_SupertrendBurstScalperTradeV4.mq5"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def extract_function(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise AssertionError(f"unterminated function: {signature}")


def money_required_free(
    equity: float,
    call: float,
    stop: float,
    reserve_factor: float = 0.20,
    floor_pct: float = 1.0,
) -> float | None:
    protected = max(call, stop)
    if not all(math.isfinite(x) for x in (equity, call, stop)) or equity <= protected:
        return None
    reserve = max((equity - protected) * reserve_factor, equity * floor_pct / 100.0)
    return protected + reserve


def test_identity_and_zero_send_audit_guard_are_frozen() -> None:
    text = source_text()
    assert '#property version   "5.00"' in text
    assert 'InpHypothesisId        = "HYP-STBS-XAUUSD-M15-016"' in text
    assert 'InpVariantTag          = "STBS_H1_FLIP_M15_BURST_AUDIT_V5_ACCOUNT_SAFE"' in text
    assert "InpMagic               = 5604116" in text
    assert 'const string EA_NAME              = "EA_SupertrendBurstScalperTradeV5"' in text
    assert "!InpAuditOnly || InpEnableTelemetry" in text
    for signature in (
        "bool SubmitCancelOrder(",
        "bool SubmitClose(",
        "bool SubmitEntry(",
    ):
        body = extract_function(text, signature)
        assert "if(InpAuditOnly)" in body
        assert "OrderSend(" in body
        assert body.index("if(InpAuditOnly)") < body.index("OrderSend(")


def test_signal_geometry_and_lifecycle_functions_match_v4_exactly() -> None:
    current = source_text()
    parent = V4_SOURCE.read_text(encoding="utf-8")
    for signature in (
        "bool RebuildFrozenSupertrend(",
        "bool BuildEntryGeometry(",
        "bool ProcessNewClosedH1Bars(",
        "bool SubmitEntry(",
        "void ManageLifecycle(",
    ):
        assert extract_function(current, signature) == extract_function(parent, signature)


def test_money_mode_boundary_and_exact_fivepercent_capacity() -> None:
    assert money_required_free(92_000.0, 92_000.0, 90_000.0) is None
    assert money_required_free(90_000.0, 92_000.0, 90_000.0) is None
    assert money_required_free(100_000.0, 92_000.0, 90_000.0) == 93_600.0
    required = money_required_free(100_000.0, 92_000.0, 90_000.0)
    assert required is not None
    assert 100_000.0 - required == 6_400.0
    assert min(100_000.0 * 0.05, 100_000.0 - required) == 5_000.0


def test_money_mode_formula_is_identical_in_candidate_and_actual_checks() -> None:
    text = source_text()
    candidate = extract_function(text, "MarginSafetyResult EvaluateMarginCandidate(")
    actual = extract_function(text, "MarginSafetyResult EvaluateActualMargin(")
    for fragment in (
        "const double protected_level=MathMax(so_call,so_stop);",
        "const double remaining_headroom=",
        "InpMoneyHeadroomReserveFactor",
        "InpMoneyFreeEquityFloorPct/100.0",
        "threshold=protected_level+reserve;",
    ):
        assert fragment in candidate
        assert fragment in actual
    assert "check.margin_free>=threshold && check.equity-check.margin>=threshold" in candidate
    assert "free_margin>=threshold && equity-margin>=threshold" in actual
    assert "required_margin>equity*InpMaxNewPositionMarginPct/100.0" in candidate
    assert "candidate=NormalizeDouble(candidate-step,digits);" in text


def test_percent_mode_remains_v4_contract() -> None:
    text = source_text()
    assert "MathMax(InpMinProjectedMarginLevelPct," in text
    assert "MathMax(so_call,so_stop)*InpPercentStopoutHeadroomFactor" in text
    assert "InpPercentStopoutHeadroomFactor!=1.25" in text


def test_audit_logging_is_bounded_and_retains_formula_evidence() -> None:
    text = source_text()
    candidate = extract_function(text, "MarginSafetyResult EvaluateMarginCandidate(")
    selector = extract_function(text, "bool SelectMarginSafeVolume(")
    assert 'if(!InpAuditOnly)\n      PrintFormat("STBS_MARGIN_CHECK|' in candidate
    assert 'if(!InpAuditOnly)\n      Print("STBS_MARGIN_REJECT|' in selector
    compact = (
        "STBS_SIGNAL|source_epoch=1547560800|decision_epoch=1547564400|"
        "direction=LONG|exact_next=true|atr_ready=true|geometry_ready=true|"
        "margin_ready=true|volume=0.09000000|projected_free=99500.00000000|"
        "required_free=93600.00000000|audit=true"
    )
    # Two journal roots plus a conservative 120-byte terminal prefix per row.
    estimated = 2 * 690 * (len(compact.encode("utf-8")) + 120)
    assert estimated < 700_000
    assert "volume=%.8f|projected_free=%.8f|required_free=%.8f|audit=true" in text


def test_invalid_account_inputs_fail_closed() -> None:
    text = source_text()
    candidate = extract_function(text, "MarginSafetyResult EvaluateMarginCandidate(")
    assert "!MathIsValidNumber(equity) || equity<=0.0" in candidate
    assert "!OrderCalcMargin(" in candidate
    assert "!OrderCheck(request,check)" in candidate
    assert "return MARGIN_SAFETY_FATAL;" in candidate
    assert "if(result==MARGIN_SAFETY_FATAL)" in text
    assert 'FailRuntime("margin_candidate_evaluation_failed")' in text
