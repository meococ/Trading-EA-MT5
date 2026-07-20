import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
SOURCE = ROOT / "EA_ICTFVGReportFidelity.mq5"
RECEIPT = ROOT / "research" / "evidence" / "20260719_SOURCE_BINARY_RECEIPT_V31.json"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def function_body(name: str) -> str:
    text = source_text()
    signature = text.index(f"{name}(")
    opening = text.index("{", signature)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening : index + 1]
    raise AssertionError(f"unterminated function: {name}")


def test_daily_rollover_does_not_erase_cross_day_loss_streak() -> None:
    body = function_body("ResetRiskDayIfNeeded")
    assert "g_trades_today=0" in body
    assert "g_consecutive_losses=0" not in body
    assert "g_cooldown_until=0" not in body


def test_position_risk_state_is_persisted_and_rehydrated_by_position_id() -> None:
    save = function_body("SavePersistentRiskState")
    load = function_body("LoadPersistentRiskState")
    restore = function_body("RestoreOwnedPositionState")
    for key in (
        "poslo", "poshi", "classlo", "classhi", "planrisk", "lifenet",
        "entryday", "force", "forcesince",
    ):
        assert f'PersistentKey("{key}")' in save
        assert f'PersistentKey("{key}")' in load
    assert "g_position_identifier==position_id" in restore
    assert "LifecycleStatsFromHistory(position_id,history_net,history_last_deal_time)" in restore
    assert "g_position_identifier=(position_high<<32)|position_low" in load
    assert "!same_position || !stored_stop_valid || g_planned_risk_account<=0.0" in restore
    assert "g_force_close=true" in restore


def test_lifecycle_counters_advance_on_first_actual_deal_not_send_request() -> None:
    send = function_body("TryOpenTrade")
    lifecycle = function_body("LogLifecycleDeal")
    assert "g_entries_opened++" not in send
    assert "g_trades_today++" not in send
    assert "bool first_open=" in lifecycle
    assert "g_entries_opened++" in lifecycle
    assert "g_trades_today++" in lifecycle
    assert "LifecycleStatsFromHistory(position_id,authoritative_net" in lifecycle


def test_server_retcode_pending_order_and_fill_risk_retry_are_fail_closed() -> None:
    can_open = function_body("CanOpenNow")
    send = function_body("TryOpenTrade")
    reconcile = function_body("ReconcileActualFillRisk")
    manage = function_body("ManageOwnedPosition")
    emergency = function_body("ForceCloseOwnedPosition")
    assert "OwnedPendingOrderExists()" in can_open
    assert "TradeRetcodeAccepted(retcode)" in send
    assert "PositionGetDouble(POSITION_PRICE_OPEN)" in reconcile
    assert "ForceCloseOwnedPosition(" in reconcile
    assert "if(g_force_close)" in manage
    assert "TradeRetcodeAccepted(retcode)" in emergency


def test_peak_equity_is_persisted_when_new_high_is_observed() -> None:
    on_tick = function_body("OnTick")
    assert "if(equity>g_peak_equity)" in on_tick
    assert 'GlobalVariableSet(PersistentKey("peak"),g_peak_equity)' in on_tick


def test_offline_close_replay_is_idempotent_and_daily_cap_uses_actual_deals() -> None:
    restore = function_body("RestoreOwnedPositionState")
    classify = function_body("ApplyLifecycleClassification")
    count_entries = function_body("CountActualEntryLifecyclesForUtcDay")
    on_init = function_body("OnInit")
    assert "ApplyLifecycleClassification(closed_position_id,closed_net,final_deal_time)" in restore
    assert "position_id==g_last_classified_position_identifier" in classify
    assert "cooldown_anchor=(final_deal_time>0 ? final_deal_time : TimeCurrent())" in classify
    assert "g_last_classified_position_identifier=position_id" in classify
    assert "DEAL_POSITION_ID" in count_entries
    assert "UtcDateKey(deal_time)!=date_key" in count_entries
    assert "CountActualEntryLifecyclesForUtcDay(g_day_key)" in on_init


def test_current_source_binary_receipt_is_fully_hash_bound() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert (
        receipt["hypothesis_id"]
        == "HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"
    )
    bindings = [
        receipt["source"],
        *receipt["compile_dependencies"],
        receipt["binary"],
        receipt["compile_log"],
        receipt["preregistration"],
        receipt["preset"],
        receipt["nonrepaint_audit"],
    ]
    for binding in bindings:
        path = WORKSPACE / binding["path"]
        assert path.is_file(), binding["path"]
        assert path.stat().st_size == binding["bytes"]
        assert sha256(path) == binding["sha256"]
    assert receipt["compile_log"]["errors"] == 0
    assert receipt["compile_log"]["warnings"] == 0
    assert receipt["nonrepaint_audit"]["status"] == "PASS"
