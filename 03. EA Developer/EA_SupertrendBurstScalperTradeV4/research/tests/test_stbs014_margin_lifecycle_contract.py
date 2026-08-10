from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV4.mq5"
PARENT = PACKAGE.parent / "EA_SupertrendBurstScalperTradeV3" / "EA_SupertrendBurstScalperTradeV3.mq5"
EX5 = PACKAGE / "EA_SupertrendBurstScalperTradeV4.ex5"
LOG = PACKAGE / "EA_SupertrendBurstScalperTradeV4.log"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8-sig")


def function_body(text: str, name: str) -> str:
    match = re.search(
        rf"(?m)^(?:bool|void|int|double|string|datetime|ulong|long)\s+{re.escape(name)}\s*\([^;]*?\)\s*\n\{{",
        text,
    )
    assert match, name
    depth = 1
    index = match.end()
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0, name
    return text[match.start():index]


def test_identity_and_compile_checkpoint() -> None:
    text = source()
    assert 'InpHypothesisId        = "HYP-STBS-XAUUSD-M15-014";' in text
    assert 'InpMagic               = 5604114;' in text
    assert 'const string EA_NAME              = "EA_SupertrendBurstScalperTradeV4";' in text
    assert SOURCE.read_text(encoding="utf-8-sig").count("\n") >= 2400
    assert EX5.is_file() and EX5.stat().st_size > 0
    assert "Result: 0 errors, 0 warnings" in LOG.read_text(encoding="utf-16")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == "028D0AADB49856F58B167390E93300CD12AD90993F13FE7D5012DE6FFB8FC726"


def test_strategy_geometry_is_not_rescued() -> None:
    text = source()
    for frozen in (
        "InpRiskPercent         = 0.25;",
        "InpStopAtrMult         = 1.00;",
        "InpTargetRR            = 1.50;",
        "InpMaxHoldBars         = 8;",
        "const int ST_ATR_PERIOD          = 10;",
        "const double ST_FACTOR           = 3.0;",
        "const int M15_ATR_PERIOD         = 14;",
    ):
        assert frozen in text
    assert "MathFloor((risk_cash/MathAbs(one_lot_profit))/step)*step" in text
    assert "raw_stop=direction>0 ? entry-InpStopAtrMult*atr" in text
    assert "raw_target=direction>0 ? entry+InpTargetRR*risk_distance" in text
    assert "bars[index].time>=DESIGN_START_TIME && bars[index].time<DESIGN_END_TIME" in text
    for forbidden in ("ProfitFactor", "Sharpe", "recovery factor", "session filter"):
        assert forbidden not in text


def test_signal_atr_clock_and_risk_core_are_byte_identical_to_hyp013() -> None:
    parent = PARENT.read_text(encoding="utf-8-sig")
    current = source()
    for name in (
        "AdvanceSupertrend",
        "RebuildFrozenSupertrend",
        "EntryClockAllowed",
        "FlattenRequired",
        "RiskSizedVolume",
        "ClosedM15AtrAtDecision",
        "ProcessNewClosedH1Bars",
    ):
        assert function_body(current, name) == function_body(parent, name), name


def test_margin_selection_is_stepwise_and_broker_aware() -> None:
    text = source()
    required = (
        "InpMaxNewPositionMarginPct     = 5.00;",
        "InpMinProjectedMarginLevelPct  = 2000.00;",
        "InpStopoutHeadroomFactor       = 1.25;",
        "ACCOUNT_MARGIN_SO_MODE",
        "ACCOUNT_MARGIN_SO_CALL",
        "ACCOUNT_MARGIN_SO_SO",
        "OrderCalcMargin(plan.order_type,_Symbol,volume,plan.entry,required_margin)",
        "OrderCheck(request,check)",
        "check.margin_level>=threshold",
        "candidate=NormalizeDouble(candidate-step,digits)",
        'Print("STBS_MARGIN_REJECT|min_volume_unsafe=true")',
    )
    for marker in required:
        assert marker in text
    margin = text[text.index("MarginSafetyResult EvaluateMarginCandidate"):text.index("bool SelectMarginSafeVolume")]
    assert margin.index("OrderCalcMargin(plan.order_type") < margin.index("OrderCheck(request,check)")
    assert "required_margin>equity*InpMaxNewPositionMarginPct/100.0" in text


def test_actual_margin_and_forced_stopout_fail_closed() -> None:
    text = source()
    assert "MarginSafetyResult EvaluateActualMargin()" in text
    assert 'SetExitIntent(EXIT_RUNTIME_FAULT);' in text
    assert "deal_reason==DEAL_REASON_SO" in text
    assert 'PrintFormat("STBS_FATAL|broker_stopout' in text
    assert "PositionOpenedByThisEa(position_id)" in text
    transaction = text[text.index("void OnTradeTransaction"):]
    assert "PositionOpenedByThisEa(position_id)" in transaction
    assert "HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)==InpMagic" not in transaction
    assert "const ENUM_DEAL_REASON deal_reason=" in transaction
    assert "EnumToString(deal_reason)" in transaction


def test_deinit_reconciles_before_runmeta_and_is_idempotent() -> None:
    text = source()
    deinit = text[text.index("void OnDeinit"):text.index("void OnTick")]
    assert deinit.index("ReconcileLifecycleHistory()") < deinit.index("WriteRunMeta()")
    assert "g_lifecycle_positions_opened!=g_lifecycle_positions_final_closed" in deinit
    assert "DealAlreadyLogged(deal)" in text
    assert "MarkDealLogged(deal)" in text
    assert "RecoverTelemetryContextFromHistory(position_id)" in text
    assert "MarkUniquePosition(g_open_position_ids,position_id,added)" in text
    assert "MarkUniquePosition(g_closed_position_ids,position_id,added)" in text
    assert '"deal_reason"' in text
    assert 'g_run_id=StringFormat("%s_%I64d",InpHypothesisId,InpMagic);' in text
    assert "LoadExistingLifecycleState()" in text
    assert "for(int pass=0;pass<2;pass++)" in text
    assert "PositionWasLoggedOpen(position_id)" in text
    assert 'PrintFormat("STBS_DEAL_DEFER' in text
    assert "RegisterForcedStopout(transaction.deal,position_id)" in text
    assert "PositionDealVolumesThrough(position_id,deal,open_volume,close_volume)" in text
    assert "DEAL_TIME_MSC" in text
    assert "candidate_time_msc==target_time_msc && deal>through_deal" in text


def test_partial_fill_replay_has_only_one_final_close() -> None:
    deals = [
        (1000, 1, "IN", 0.06),
        (1000, 2, "IN", 0.04),
        (2000, 3, "OUT", 0.03),
        (3000, 4, "OUT", 0.07),
    ]
    ordered = sorted(deals)
    open_volume = 0.0
    close_volume = 0.0
    final_flags: list[bool] = []
    for _, _, entry, volume in ordered:
        if entry == "IN":
            open_volume += volume
        else:
            close_volume += volume
            final_flags.append(close_volume + 1e-8 >= open_volume)
    assert final_flags == [False, True]


def test_audit_only_guards_every_ordersend_gateway() -> None:
    text = source()
    for name in ("SubmitEntry", "SubmitClose", "SubmitCancelOrder"):
        start = text.index(f"bool {name}")
        next_function = re.search(r"\n(?:bool|void|int|double|string|datetime|ulong|long|MarginSafetyResult)\s+\w+\s*\(", text[start + 5 :])
        end = len(text) if next_function is None else start + 5 + next_function.start()
        body = text[start:end]
        assert "if(InpAuditOnly)" in body
        assert body.index("if(InpAuditOnly)") < body.index("OrderSend(")


def test_hyp014_runtime_package_is_audit_only_telemetry_none() -> None:
    text = source()
    contract = json.loads((PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json").read_text(encoding="utf-8"))
    assert "input bool   InpEnableTelemetry     = false;" in text
    assert "!InpAuditOnly || InpEnableTelemetry" in text
    assert "if(InpEnableTelemetry && (!OpenTelemetry() || !RecoverTelemetryPositionContext()))" in text
    assert "if(InpEnableTelemetry && !ReconcileLifecycleHistory())" in text
    assert contract["telemetry_profile"] == "none"
